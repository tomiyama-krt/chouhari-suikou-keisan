import streamlit as st
import pandas as pd

st.set_page_config(page_title="丁張り勾配計算", page_icon="📐", layout="centered")

PVC_OUTER_DIAMETER = {
    100: 114, 125: 140, 150: 165, 200: 216, 250: 267,
    300: 318, 350: 370, 400: 420, 450: 470, 500: 520,
}


def num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if pd.isna(f):
        return None
    return f


def fmt(v, digits=3):
    n = num(v)
    if n is None:
        return "–"
    return f"{n:.{digits}f}"


def fmt_signed(v, digits=0):
    n = num(v)
    if n is None:
        return "–"
    sign = "+" if n >= 0 else "−"
    return f"{sign}{abs(n):.{digits}f}"


def fmt_slope(per_m, unit):
    if per_m is None:
        return "–"
    direction = "下り" if per_m >= 0 else "上り"
    if unit == "%":
        return f"{direction} {abs(per_m) * 100:.1f}%"
    if per_m == 0:
        return "–"
    return f"{direction} 1/{abs(1 / per_m):.1f}"


# ============================================================
# 丁張り計算
# ============================================================
def tou_sample_rows():
    return [
        {"name": "No.1", "reading": 0.856, "design": 12.700},
        {"name": "No.2", "reading": 0.640, "design": 13.000},
    ]


def render_tou():
    st.subheader("① 器械高の設定")
    c1, c2, c3 = st.columns(3)
    bm_name = c1.text_input("基準点名", value=st.session_state.get("tou_bm_name", "BM-1"), key="tou_bm_name")
    bm_elev = c2.number_input(
        "基準点 既知標高 (m)", value=st.session_state.get("tou_bm_elev", 12.500),
        step=0.001, format="%.3f", key="tou_bm_elev",
    )
    bs = c3.number_input(
        "後視 読値 BS (m)", value=st.session_state.get("tou_bs", 1.234),
        step=0.001, format="%.3f", key="tou_bs",
    )

    ih = None
    if bm_elev is not None and bs is not None:
        ih = bm_elev + bs
    st.metric("器械高 IH", fmt(ih) if ih is not None else "–")

    st.subheader("② 測点 (貫板の下がり量)")
    if "tou_rows" not in st.session_state:
        st.session_state.tou_rows = tou_sample_rows()

    delete_idx = None
    for idx, row in enumerate(st.session_state.tou_rows):
        with st.container(border=True):
            top1, top2 = st.columns([4, 1])
            top1.markdown(f"**測点 {idx + 1}**")
            if top2.button("削除", key=f"tou_del_{idx}", use_container_width=True):
                delete_idx = idx

            c1, c2, c3 = st.columns(3)
            row["name"] = c1.text_input(
                "測点名", value=row.get("name") or f"No.{idx + 1}", key=f"tou_name_{idx}"
            )
            row["reading"] = c2.number_input(
                "仮天端 読値 (m)", value=row.get("reading"), step=0.001, format="%.3f", key=f"tou_reading_{idx}"
            )
            row["design"] = c3.number_input(
                "設計 計画高 (m)", value=row.get("design"), step=0.001, format="%.3f", key=f"tou_design_{idx}"
            )

            reading, design = row["reading"], row["design"]
            board_elev = (ih - reading) if (ih is not None and reading is not None) else None
            target_reading = (ih - design) if (ih is not None and design is not None) else None
            drop_mm = ((board_elev - design) * 1000) if (board_elev is not None and design is not None) else None

            r1, r2, r3 = st.columns(3)
            r1.caption("仮天端標高")
            r1.markdown(f"##### {fmt(board_elev) if board_elev is not None else '–'}")
            r2.caption("読むべき値")
            r2.markdown(f"##### {fmt(target_reading) if target_reading is not None else '–'}")
            r3.caption("下がり量")
            r3.markdown(f"##### {f'{fmt_signed(drop_mm, 0)} mm' if drop_mm is not None else '–'}")

    if delete_idx is not None:
        st.session_state.tou_rows.pop(delete_idx)
        st.rerun()

    if st.button("＋ 測点を追加", key="tou_add_btn"):
        n = len(st.session_state.tou_rows) + 1
        st.session_state.tou_rows.append({"name": f"No.{n}", "reading": None, "design": None})
        st.rerun()

    st.caption(
        "器械高 IH ＝ 基準点標高 ＋ 後視読値。各測点で仮天端を前視で読むと仮天端標高が求まり、"
        "設計計画高を入れると「読むべき値」と「仮天端からの下がり量」を自動計算します。"
        "下がり量がプラスなら仮天端から下げる、マイナスなら上げる印です。"
    )

    if st.button("サンプルを読込", key="tou_sample_btn"):
        st.session_state.tou_rows = tou_sample_rows()
        st.rerun()


# ============================================================
# 雨水排水勾配 (分岐・合流に対応したネットワーク構造)
# ============================================================
def sui_next_id(items):
    return max((it["id"] for it in items), default=0) + 1


def sui_sample_nodes():
    return [
        {"id": 1, "name": "No.1桝", "reading": 1.858, "out": None,
         "pipe_type": "VU管", "nominal_size": 200, "outer_diameter": None},
        {"id": 2, "name": "No.2桝", "reading": 1.998, "out": None,
         "pipe_type": "VU管", "nominal_size": 200, "outer_diameter": None},
        {"id": 3, "name": "No.3桝", "reading": 1.978, "out": None,
         "pipe_type": "VU管", "nominal_size": 200, "outer_diameter": None},
        {"id": 4, "name": "No.4桝", "reading": None, "out": 11.656,
         "pipe_type": "VU管", "nominal_size": 200, "outer_diameter": None},
    ]


def sui_sample_edges():
    return [
        {"id": 1, "from_id": 1, "to_id": 2, "dist": 6.0, "reading": None, "invert": None},
        {"id": 2, "from_id": 1, "to_id": 3, "dist": 5.0, "reading": None, "invert": None},
        {"id": 3, "from_id": 2, "to_id": 4, "dist": 4.0, "reading": None, "invert": None},
        {"id": 4, "from_id": 3, "to_id": 4, "dist": 4.0, "reading": None, "invert": None},
    ]


def outer_diameter_mm(pipe_type, nominal_size, outer_diameter):
    if pipe_type in ("VU管", "VP管"):
        nd = num(nominal_size)
        if nd is not None and int(nd) in PVC_OUTER_DIAMETER:
            return PVC_OUTER_DIAMETER[int(nd)]
        return None
    return num(outer_diameter)


def compute_network(nodes, edges, ih, unit):
    node_out, node_od = {}, {}
    for n in nodes:
        reading = num(n.get("reading"))
        out_direct = num(n.get("out"))
        out = (ih - reading) if (reading is not None and ih is not None) else out_direct
        node_out[n["id"]] = out
        node_od[n["id"]] = outer_diameter_mm(n.get("pipe_type"), n.get("nominal_size"), n.get("outer_diameter"))

    edge_results = []
    for e in edges:
        upstream_out = node_out.get(e.get("from_id"))
        downstream_out = node_out.get(e.get("to_id"))
        reading = num(e.get("reading"))
        invert_direct = num(e.get("invert"))
        if reading is not None and ih is not None:
            IN = ih - reading
        elif invert_direct is not None:
            IN = invert_direct
        else:
            IN = downstream_out  # 未指定なら下流桝のOUTをそのまま流入管底高として扱う(単純接続の場合)

        dist = num(e.get("dist"))
        per_m = None
        if upstream_out is not None and IN is not None and dist is not None and dist > 0:
            per_m = (upstream_out - IN) / dist

        local_drop_mm = ((downstream_out - IN) * 1000) if (downstream_out is not None and IN is not None) else None

        edge_results.append({
            "edge": e, "in": IN, "per_m": per_m, "dist": dist,
            "upstream_out": upstream_out, "local_drop_mm": local_drop_mm,
        })

    return node_out, node_od, edge_results


def render_sui():
    st.subheader("① 器械高・単位の設定")
    c1, c2, c3 = st.columns(3)
    bm_name = c1.text_input("基準点名", value=st.session_state.get("sui_bm_name", "BM-1"), key="sui_bm_name")
    bm_elev = c2.number_input(
        "基準点 既知標高 (m)", value=st.session_state.get("sui_bm_elev", 12.500),
        step=0.001, format="%.3f", key="sui_bm_elev",
    )
    bs = c3.number_input(
        "後視 読値 BS (m)", value=st.session_state.get("sui_bs", 1.234),
        step=0.001, format="%.3f", key="sui_bs",
    )

    ih = None
    if bm_elev is not None and bs is not None:
        ih = bm_elev + bs
    st.metric("器械高 IH", fmt(ih) if ih is not None else "–")

    unit = st.radio("勾配の単位", ["%", "分数 1/n"], horizontal=True, key="sui_unit")
    unit_key = "%" if unit == "%" else "frac"
    show_crown = st.toggle("管天端高を表示する", value=st.session_state.get("sui_show_crown", True), key="sui_show_crown")
    st.caption("VU管・VP管の外径は一般的な参考値です(同呼び径では共通の外径として扱っています)。実際の外径は必ずメーカーカタログ・仕様書で確認してください。")

    if "sui_nodes" not in st.session_state:
        st.session_state.sui_nodes = sui_sample_nodes()
    if "sui_edges" not in st.session_state:
        st.session_state.sui_edges = sui_sample_edges()

    pipe_options = ["VU管", "VP管", "その他"]
    size_options = list(PVC_OUTER_DIAMETER.keys())

    # ===== 桝リスト =====
    st.subheader("② 桝リスト")
    delete_node_id = None
    for node in st.session_state.sui_nodes:
        nid = node["id"]
        with st.container(border=True):
            top1, top2 = st.columns([4, 1])
            top1.markdown(f"**{node.get('name') or f'桝{nid}'}**")
            if top2.button("削除", key=f"sui_node_del_{nid}", use_container_width=True):
                delete_node_id = nid

            c1, c2, c3 = st.columns(3)
            node["name"] = c1.text_input(
                "桝名", value=node.get("name") or f"桝{nid}", key=f"sui_node_name_{nid}"
            )
            node["reading"] = c2.number_input(
                "読値 (m)", value=node.get("reading"), step=0.001, format="%.3f", key=f"sui_node_reading_{nid}"
            )
            node["out"] = c3.number_input(
                "OUT 直接入力 (m)", value=node.get("out"), step=0.001, format="%.3f", key=f"sui_node_out_{nid}"
            )

            c4, c5 = st.columns(2)
            current_pipe = node.get("pipe_type") or "VU管"
            node["pipe_type"] = c4.selectbox(
                "管種(下流方向)", pipe_options,
                index=pipe_options.index(current_pipe) if current_pipe in pipe_options else 0,
                key=f"sui_node_pipe_{nid}",
            )
            if node["pipe_type"] in ("VU管", "VP管"):
                current_size = node.get("nominal_size")
                node["nominal_size"] = c5.selectbox(
                    "呼び径(mm)", size_options,
                    index=size_options.index(current_size) if current_size in size_options else 0,
                    key=f"sui_node_size_{nid}",
                )
            else:
                node["outer_diameter"] = c5.number_input(
                    "外径入力(mm)", value=node.get("outer_diameter"), step=1.0, format="%.0f", key=f"sui_node_od_{nid}"
                )

    if delete_node_id is not None:
        st.session_state.sui_nodes = [n for n in st.session_state.sui_nodes if n["id"] != delete_node_id]
        st.session_state.sui_edges = [
            e for e in st.session_state.sui_edges
            if e["from_id"] != delete_node_id and e["to_id"] != delete_node_id
        ]
        st.rerun()

    if st.button("＋ 桝を追加", key="sui_node_add_btn"):
        new_id = sui_next_id(st.session_state.sui_nodes)
        st.session_state.sui_nodes.append({
            "id": new_id, "name": f"桝{new_id}", "reading": None, "out": None,
            "pipe_type": "VU管", "nominal_size": None, "outer_diameter": None,
        })
        st.rerun()

    st.caption("読値を入れるとその桝のOUT(流出管底高)を自動計算します(読値が優先、空欄ならOUT直接入力を使用)。")

    # ===== 区間リスト =====
    st.subheader("③ 区間 (上流桝 → 下流桝)")
    node_options = [n["id"] for n in st.session_state.sui_nodes]
    node_name_by_id = {n["id"]: (n.get("name") or f"桝{n['id']}") for n in st.session_state.sui_nodes}

    if len(node_options) < 2:
        st.info("区間を追加するには桝が2つ以上必要です。")
    else:
        delete_edge_id = None
        for edge in st.session_state.sui_edges:
            eid = edge["id"]
            with st.container(border=True):
                top1, top2 = st.columns([4, 1])
                from_label = node_name_by_id.get(edge.get("from_id"), "?")
                to_label = node_name_by_id.get(edge.get("to_id"), "?")
                top1.markdown(f"**{from_label} → {to_label}**")
                if top2.button("削除", key=f"sui_edge_del_{eid}", use_container_width=True):
                    delete_edge_id = eid

                c1, c2, c3 = st.columns(3)
                cur_from = edge.get("from_id") if edge.get("from_id") in node_options else node_options[0]
                edge["from_id"] = c1.selectbox(
                    "上流桝", node_options, index=node_options.index(cur_from),
                    format_func=lambda i: node_name_by_id.get(i, "?"), key=f"sui_edge_from_{eid}",
                )
                cur_to = edge.get("to_id") if edge.get("to_id") in node_options else node_options[0]
                edge["to_id"] = c2.selectbox(
                    "下流桝", node_options, index=node_options.index(cur_to),
                    format_func=lambda i: node_name_by_id.get(i, "?"), key=f"sui_edge_to_{eid}",
                )
                edge["dist"] = c3.number_input(
                    "距離(m)", value=edge.get("dist"), step=0.1, format="%.1f", key=f"sui_edge_dist_{eid}"
                )

                c4, c5 = st.columns(2)
                edge["reading"] = c4.number_input(
                    "読値(m・任意)", value=edge.get("reading"), step=0.001, format="%.3f", key=f"sui_edge_reading_{eid}"
                )
                edge["invert"] = c5.number_input(
                    "IN 直接入力(m・任意)", value=edge.get("invert"), step=0.001, format="%.3f", key=f"sui_edge_invert_{eid}"
                )

        if delete_edge_id is not None:
            st.session_state.sui_edges = [e for e in st.session_state.sui_edges if e["id"] != delete_edge_id]
            st.rerun()

        if st.button("＋ 区間を追加", key="sui_edge_add_btn"):
            new_id = sui_next_id(st.session_state.sui_edges)
            st.session_state.sui_edges.append({
                "id": new_id, "from_id": node_options[0], "to_id": node_options[-1],
                "dist": None, "reading": None, "invert": None,
            })
            st.rerun()

    st.caption(
        "区間の「読値」「IN直接入力」を両方空欄にすると、下流桝のOUTをそのままINとして扱います"
        "(単純な1本つなぎならこれで十分です)。合流点のように複数の区間が同じ下流桝に集まる場合は、"
        "区間ごとに読値やINを入れて個別に管理できます。"
    )

    node_out, node_od, edge_results = compute_network(
        st.session_state.sui_nodes, st.session_state.sui_edges, ih, unit_key
    )

    # ===== 桝の計算結果 =====
    st.subheader("④ 桝の計算結果")
    node_rows = []
    for n in st.session_state.sui_nodes:
        out = node_out.get(n["id"])
        od = node_od.get(n["id"])
        crown = (out + od / 1000) if (out is not None and od is not None) else None
        row = {"桝名": n.get("name"), "OUT 流出管底高": fmt(out) if out is not None else "–"}
        if show_crown:
            row["管天端高(OUT)"] = fmt(crown) if crown is not None else "–"
        node_rows.append(row)
    st.dataframe(pd.DataFrame(node_rows), use_container_width=True, hide_index=True)

    # ===== 区間の計算結果 =====
    st.subheader("⑤ 区間の計算結果")
    edge_rows = []
    for r in edge_results:
        e = r["edge"]
        from_label = node_name_by_id.get(e.get("from_id"), "?")
        to_label = node_name_by_id.get(e.get("to_id"), "?")
        edge_rows.append({
            "区間": f"{from_label} → {to_label}",
            "距離(m)": fmt(r["dist"], 1) if r["dist"] is not None else "–",
            "IN(下流桝への流入管底高)": fmt(r["in"]) if r["in"] is not None else "–",
            "勾配": fmt_slope(r["per_m"], unit_key),
            "桝内落差(mm)": fmt_signed(r["local_drop_mm"], 0) if r["local_drop_mm"] is not None else "–",
        })
    st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)

    # ===== 区間内の中間管底高 =====
    st.subheader("⑥ 区間内の中間管底高")
    interval = st.number_input(
        "表示間隔 (m)", value=st.session_state.get("sui_interval", 2.0),
        step=0.1, format="%.1f", min_value=0.1, key="sui_interval",
    )

    any_shown = False
    if interval is not None and interval > 0:
        for r in edge_results:
            e = r["edge"]
            per_m, dist, upstream_out = r["per_m"], r["dist"], r["upstream_out"]
            if per_m is None or dist is None or dist <= 0 or upstream_out is None:
                continue
            any_shown = True
            from_label = node_name_by_id.get(e.get("from_id"), "?")
            to_label = node_name_by_id.get(e.get("to_id"), "?")
            seg_od = node_od.get(e.get("from_id"))

            points = []
            x = 0.0
            while x < dist - 1e-9:
                points.append(x)
                x += interval
            points.append(dist)

            sub_rows = []
            for d in points:
                inv = upstream_out - per_m * d
                reading_val = (ih - inv) if ih is not None else None
                row = {"起点からの距離": fmt(d, 1), "管底高": fmt(inv), "読み値": fmt(reading_val) if reading_val is not None else "–"}
                if show_crown:
                    crown = (inv + seg_od / 1000) if seg_od is not None else None
                    row["管天端高"] = fmt(crown) if crown is not None else "–"
                sub_rows.append(row)

            st.markdown(f"**{from_label} → {to_label}** ({fmt_slope(per_m, unit_key)})")
            st.dataframe(pd.DataFrame(sub_rows), use_container_width=True, hide_index=True)

    if not any_shown:
        st.caption("上流桝のOUT・距離・INがそろった区間から、中間管底高が表示されます。")

    if st.button("サンプルを読込", key="sui_sample_btn"):
        st.session_state.sui_nodes = sui_sample_nodes()
        st.session_state.sui_edges = sui_sample_edges()
        st.rerun()


# ============================================================
# メイン
# ============================================================
st.title("丁張り勾配計算")

tab1, tab2 = st.tabs(["丁張り計算", "雨水排水勾配"])
with tab1:
    render_tou()
with tab2:
    render_sui()
