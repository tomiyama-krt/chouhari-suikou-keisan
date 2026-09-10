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
def tou_sample_df():
    return pd.DataFrame(
        [
            {"測点名": "No.1", "貫天端読値": 0.856, "設計計画高": 12.700},
            {"測点名": "No.2", "貫天端読値": 0.640, "設計計画高": 13.000},
        ]
    )


def compute_tou(df, ih):
    board_elev, target_reading, drop_mm = [], [], []
    for _, row in df.iterrows():
        reading = num(row.get("貫天端読値"))
        design = num(row.get("設計計画高"))
        be = (ih - reading) if (ih is not None and reading is not None) else None
        tr = (ih - design) if (ih is not None and design is not None) else None
        dr = ((be - design) * 1000) if (be is not None and design is not None) else None
        board_elev.append(be)
        target_reading.append(tr)
        drop_mm.append(dr)
    out = df.copy()
    out["仮天端標高"] = board_elev
    out["読むべき値"] = target_reading
    out["下がり量(mm)"] = drop_mm
    return out


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
    if "tou_df" not in st.session_state:
        st.session_state.tou_df = tou_sample_df()

    if st.button("＋ 測点を追加", key="tou_add_btn"):
        n = len(st.session_state.tou_df) + 1
        new_row = pd.DataFrame([{"測点名": f"No.{n}", "貫天端読値": None, "設計計画高": None}])
        st.session_state.tou_df = pd.concat([st.session_state.tou_df, new_row], ignore_index=True)
        st.rerun()

    edited = st.data_editor(
        st.session_state.tou_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "測点名": st.column_config.TextColumn("測点名"),
            "貫天端読値": st.column_config.NumberColumn("貫天端 読値 (m)", format="%.3f", step=0.001),
            "設計計画高": st.column_config.NumberColumn("設計 計画高 (m)", format="%.3f", step=0.001),
        },
        key="tou_editor",
    )
    new_tou_df = edited[["測点名", "貫天端読値", "設計計画高"]].copy()
    new_tou_df["貫天端読値"] = pd.to_numeric(new_tou_df["貫天端読値"], errors="coerce")
    new_tou_df["設計計画高"] = pd.to_numeric(new_tou_df["設計計画高"], errors="coerce")
    for i in new_tou_df.index:
        name = new_tou_df.at[i, "測点名"]
        if name is None or (isinstance(name, float) and pd.isna(name)) or str(name).strip() == "":
            new_tou_df.at[i, "測点名"] = f"No.{i + 1}"
    st.session_state.tou_df = new_tou_df

    view = compute_tou(st.session_state.tou_df, ih)
    display = view[["測点名", "貫天端読値", "仮天端標高", "設計計画高", "読むべき値", "下がり量(mm)"]].copy()
    for col in ["貫天端読値", "仮天端標高", "設計計画高", "読むべき値"]:
        display[col] = display[col].map(lambda v: fmt(v) if pd.notna(v) else "–")
    display["下がり量(mm)"] = view["下がり量(mm)"].map(lambda v: fmt_signed(v, 0) if pd.notna(v) else "–")
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.caption(
        "器械高 IH ＝ 基準点標高 ＋ 後視読値。各測点で仮天端を前視で読むと仮天端標高が求まり、"
        "設計計画高を入れると「読むべき値」と「仮天端からの下がり量」を自動計算します。"
        "下がり量がプラスなら仮天端から下げる、マイナスなら上げる印です。"
    )

    if st.button("サンプルを読込", key="tou_sample_btn"):
        st.session_state.tou_df = tou_sample_df()
        st.rerun()


# ============================================================
# 雨水排水勾配
# ============================================================
def sui_sample_df():
    return pd.DataFrame(
        [
            {"桝名": "No.1桝", "桝間距離(m)": None, "読値": 1.858, "IN(流入管底高)": None, "落差(mm)": 20.0,
             "管種": "VU管", "呼び径(mm)": 200, "外径入力(mm)": None},
            {"桝名": "No.2桝", "桝間距離(m)": 6.0, "読値": 1.998, "IN(流入管底高)": None, "落差(mm)": 20.0,
             "管種": "VU管", "呼び径(mm)": 200, "外径入力(mm)": None},
            {"桝名": "No.3桝", "桝間距離(m)": 8.0, "読値": None, "IN(流入管底高)": 11.556, "落差(mm)": None,
             "管種": "VU管", "呼び径(mm)": 200, "外径入力(mm)": None},
        ]
    )


def outer_diameter_mm(pipe_type, nominal_size, outer_diameter):
    if pipe_type in ("VU管", "VP管"):
        nd = num(nominal_size)
        if nd is not None and int(nd) in PVC_OUTER_DIAMETER:
            return PVC_OUTER_DIAMETER[int(nd)]
        return None
    return num(outer_diameter)


def compute_sui(df, ih, unit):
    prev_out = None
    IN_list, OUT_list, slope_list, per_m_list, crown_list, od_list, start_invert_list, dist_list = (
        [], [], [], [], [], [], [], []
    )
    for i, row in df.iterrows():
        dist = num(row.get("桝間距離(m)"))
        reading = num(row.get("読値"))
        direct_invert = num(row.get("IN(流入管底高)"))
        drop = num(row.get("落差(mm)"))
        drop_m = (drop / 1000) if drop is not None else 0.0

        IN = None
        if reading is not None and ih is not None:
            IN = ih - reading
        elif direct_invert is not None:
            IN = direct_invert

        per_m, slope_val = None, None
        if i > 0 and IN is not None and prev_out is not None and dist is not None and dist > 0:
            per_m = (prev_out - IN) / dist
            slope_val = per_m

        OUT = (IN - drop_m) if IN is not None else None
        od = outer_diameter_mm(row.get("管種"), row.get("呼び径(mm)"), row.get("外径入力(mm)"))
        crown = (OUT + od / 1000) if (OUT is not None and od is not None) else None

        IN_list.append(IN)
        OUT_list.append(OUT)
        slope_list.append(slope_val)
        per_m_list.append(per_m if (dist is not None and dist > 0) else None)
        crown_list.append(crown)
        od_list.append(od)
        start_invert_list.append(prev_out)
        dist_list.append(dist)
        prev_out = OUT

    out = df.copy()
    out["IN計算"] = IN_list
    out["OUT"] = OUT_list
    out["勾配perM"] = slope_list
    out["区間perM"] = per_m_list
    out["管天端高OUT"] = crown_list
    out["外径mm"] = od_list
    out["区間起点OUT"] = start_invert_list
    out["距離"] = dist_list
    return out


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

    st.subheader("② 桝リスト")
    if "sui_df" not in st.session_state:
        st.session_state.sui_df = sui_sample_df()

    input_cols = ["桝名", "桝間距離(m)", "読値", "IN(流入管底高)", "落差(mm)", "管種", "呼び径(mm)", "外径入力(mm)"]

    if st.button("＋ 桝を追加", key="sui_add_btn"):
        n = len(st.session_state.sui_df) + 1
        new_row = pd.DataFrame([{
            "桝名": f"No.{n}桝", "桝間距離(m)": None, "読値": None, "IN(流入管底高)": None,
            "落差(mm)": None, "管種": "VU管", "呼び径(mm)": None, "外径入力(mm)": None,
        }])
        st.session_state.sui_df = pd.concat([st.session_state.sui_df, new_row], ignore_index=True)
        st.rerun()

    edited = st.data_editor(
        st.session_state.sui_df[input_cols],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "桝名": st.column_config.TextColumn("桝名"),
            "桝間距離(m)": st.column_config.NumberColumn("桝間距離(m)", format="%.1f", step=0.1),
            "読値": st.column_config.NumberColumn("読値 (m)", format="%.3f", step=0.001),
            "IN(流入管底高)": st.column_config.NumberColumn("IN 流入管底高 (m)", format="%.3f", step=0.001),
            "落差(mm)": st.column_config.NumberColumn("落差 (mm)", format="%.0f", step=1.0),
            "管種": st.column_config.SelectboxColumn("管種", options=["VU管", "VP管", "その他"]),
            "呼び径(mm)": st.column_config.SelectboxColumn("呼び径(mm)", options=list(PVC_OUTER_DIAMETER.keys())),
            "外径入力(mm)": st.column_config.NumberColumn("外径入力(mm・その他管種用)", format="%.0f", step=1.0),
        },
        key="sui_editor",
    )
    new_sui_df = edited[input_cols].copy()
    for col in ["桝間距離(m)", "読値", "IN(流入管底高)", "落差(mm)", "外径入力(mm)"]:
        new_sui_df[col] = pd.to_numeric(new_sui_df[col], errors="coerce")
    for i in new_sui_df.index:
        name = new_sui_df.at[i, "桝名"]
        if name is None or (isinstance(name, float) and pd.isna(name)) or str(name).strip() == "":
            new_sui_df.at[i, "桝名"] = f"No.{i + 1}桝"
    st.session_state.sui_df = new_sui_df

    calc = compute_sui(st.session_state.sui_df, ih, unit_key)

    display_cols = ["桝名", "桝間距離(m)", "読値", "IN(流入管底高)", "落差(mm)", "OUT"]
    if show_crown:
        display_cols += ["管種", "呼び径(mm)", "管天端高OUT"]
    display_cols += ["勾配perM"]

    display = calc[display_cols].copy()
    for col in ["桝間距離(m)", "読値", "IN(流入管底高)", "OUT", "管天端高OUT"]:
        if col in display.columns:
            display[col] = calc[col].map(lambda v: fmt(v) if pd.notna(v) else "–")
    if "落差(mm)" in display.columns:
        display["落差(mm)"] = calc["落差(mm)"].map(lambda v: fmt(v, 0) if pd.notna(v) else "–")
    display["勾配perM"] = calc["勾配perM"].map(lambda v: fmt_slope(v, unit_key))
    display = display.rename(columns={"OUT": "OUT 流出管底高", "管天端高OUT": "管天端高(OUT)", "勾配perM": "勾配"})
    st.dataframe(display, use_container_width=True, hide_index=True)

    # 集計
    valid = calc.dropna(subset=["距離"])
    total_len = valid["距離"].sum() if len(valid) else None
    first_out = calc["OUT"].iloc[0] if len(calc) else None
    last_valid_in = calc["IN計算"].dropna()
    last_in = last_valid_in.iloc[-1] if len(last_valid_in) else None

    m1, m2, m3 = st.columns(3)
    m1.metric("総延長", f"{total_len:.1f} m" if total_len else "–")
    if first_out is not None and last_in is not None and total_len:
        total_drop = last_in - first_out
        m2.metric("総高低差", f"{fmt_signed(total_drop * 1000, 0)} mm")
        avg_per_m = -total_drop / total_len
        m3.metric("平均勾配", fmt_slope(avg_per_m, unit_key))
    else:
        m2.metric("総高低差", "–")
        m3.metric("平均勾配", "–")

    st.subheader("③ 区間内の中間管底高")
    interval = st.number_input(
        "表示間隔 (m)", value=st.session_state.get("sui_interval", 2.0),
        step=0.1, format="%.1f", min_value=0.1, key="sui_interval",
    )

    if interval is not None and interval > 0:
        rows_data = st.session_state.sui_df.reset_index(drop=True)
        any_shown = False
        for i in range(1, len(calc)):
            per_m = calc["区間perM"].iloc[i]
            start_invert = calc["区間起点OUT"].iloc[i]
            dist = calc["距離"].iloc[i]
            if per_m is None or start_invert is None or dist is None or dist <= 0:
                continue
            any_shown = True
            from_name = rows_data["桝名"].iloc[i - 1] or f"No.{i}"
            to_name = rows_data["桝名"].iloc[i] or f"No.{i + 1}"
            seg_od = calc["外径mm"].iloc[i - 1]

            points = []
            x = 0.0
            while x < dist - 1e-9:
                points.append(x)
                x += interval
            points.append(dist)

            sub_rows = []
            for d in points:
                inv = start_invert - per_m * d
                reading_val = (ih - inv) if ih is not None else None
                row = {"起点からの距離": fmt(d, 1), "管底高": fmt(inv), "読み値": fmt(reading_val) if reading_val is not None else "–"}
                if show_crown:
                    crown = (inv + seg_od / 1000) if seg_od is not None else None
                    row["管天端高"] = fmt(crown) if crown is not None else "–"
                sub_rows.append(row)

            st.markdown(f"**{from_name} → {to_name}** ({fmt_slope(per_m, unit_key)})")
            st.dataframe(pd.DataFrame(sub_rows), use_container_width=True, hide_index=True)

        if not any_shown:
            st.caption("桝の管底高・距離がそろった区間から、中間管底高が表示されます。")
    else:
        st.caption("表示間隔(m)を入力してください。")

    st.caption(
        "各桝で「読値」「IN直接入力」のどちらかを入れれば、区間の勾配・OUTが自動計算されます(読値を優先)。"
        "「落差」は桝内でのIN→OUTの段差(mm、通常0以上)で、流出管底高 OUT = IN − 落差です。"
        "次の区間の勾配は前の桝のOUTを基準に計算します。"
    )

    if st.button("サンプルを読込", key="sui_sample_btn"):
        st.session_state.sui_df = sui_sample_df()
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
