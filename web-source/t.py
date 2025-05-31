import json
import os
import pandas as pd
import streamlit as st
from io import BytesIO
import random

# === UTILS ===

def decrypt_file(file_bytes):
    return bytearray((~b + 256) & 0xFF for b in file_bytes)

def encrypt_file(file_bytes):
    return bytearray((~b + 256) & 0xFF for b in file_bytes)

def parse_decrypted_json(file_bytes):
    data = json.loads(file_bytes.decode('utf-8'))
    parsed_chars = []
    parsed_equips = []
    parsed_arts = []
    parsed_friendship = []
    parsed_levels = []

    # === characterShards_ ===
    shards = data.get("item", {}).get("characterShards_", [])
    for entry in shards:
        char_id = entry.get("characterType")
        parsed_chars.append({
            "Category": "Z Power",
            "CharID": char_id,
            "CharLabel": "Shallot" if char_id == 9000 else str(char_id),
            "Value": entry.get("count"),
            "Editable": True
        })

    # === characterPlentyShards_ ===
    plenty = data.get("item", {}).get("characterPlentyShards_", [])
    for entry in plenty:
        char_id = entry.get("characterType")
        parsed_chars.append({
            "Category": "Awakening Z Power",
            "CharID": char_id,
            "CharLabel": "Shallot" if char_id == 9000 else str(char_id),
            "Value": entry.get("count"),
            "Editable": True
        })

    # === equipItems_ ===
    equip_items = data.get("item", {}).get("equipItems_", [])
    for entry in equip_items:
        equip_id = entry.get("equipId")
        abilities = entry.get("ability", [])
        for ab in abilities:
            params = ab.get("ability_effect_param", [])
            for idx, val in enumerate(params):
                parsed_equips.append({
                    "Category": f"Equip Effect [{idx}]",
                    "equipId": equip_id,
                    "Value": val,
                    "Editable": val != -1
                })

    # === unitInfo_ ===
    unit_info = data.get("unit", {}).get("unitInfo_", [])
    for unit in unit_info:
        char_id = unit.get("id")
        parsed_arts.append({
            "CharID": char_id,
            "strikeArtsBoost": unit.get("strikeArtsBoost", 0),
            "shotArtsBoost": unit.get("shotArtsBoost", 0),
            "specialArtsBoost": unit.get("specialArtsBoost", 0)
        })
        parsed_friendship.append({
            "CharID": char_id,
            "friendshipLevel": unit.get("friendshipLevel", 0)
        })
        parsed_levels.append({
            "CharID": char_id,
            "level": unit.get("level", 1)
        })

    return (
        pd.DataFrame(parsed_chars).sort_values("CharID"),
        pd.DataFrame(parsed_equips),
        pd.DataFrame(parsed_arts).sort_values("CharID"),
        pd.DataFrame(parsed_friendship).sort_values("CharID"),
        pd.DataFrame(parsed_levels).sort_values("CharID"),
        data
    )

def apply_mods(json_data, max_stars, zenkai7, max_equips, max_lv_arts):
    if max_stars:
        for shard in json_data["item"].get("characterShards_", []):
            if shard["characterType"] != 9000:
                shard["count"] = 9999

    if zenkai7:
        for shard in json_data["item"].get("characterPlentyShards_", []):
            shard["count"] = 7000

    if max_equips:
        for equip in json_data["item"].get("equipItems_", []):
            for ab in equip.get("ability", []):
                params = ab.get("ability_effect_param", [])
                for i, val in enumerate(params):
                    if val != -1:
                        params[i] = random.randint(350, 500)

    if max_lv_arts:
        for unit in json_data.get("unit", {}).get("unitInfo_", []):
            unit["level"] = 5000
            unit["friendshipLevel"] = 15
            unit["strikeArtsBoost"] = 99
            unit["shotArtsBoost"] = 99
            unit["specialArtsBoost"] = 99

    return json_data

# === MAIN APP ===


def main():
    st.set_page_config(page_title="DBLUMA | Editor", layout="wide", page_icon="assets/icon.png")
    st.image("assets/banner.png", use_container_width=True)
    st.warning("""
    ⚠️ Do NOT use these mods in Ranked PvP. It might result in a ban. It is okay to use in Co-Op, Raids, and Friendly PvP.
    ⚠️ Character Levels above 5,000 does NOT work in PvP. Max PvP level is 5,000.
    """)
    st.info("""
    Message from Mindset:
     If you wish to continue supporting this project and any other future projects (DBLPS) please consider joing our Discord! - https://discord.gg/NBxTbEMznf
    """)

    # --- Navigation Buttons ---
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Standard 89bb Modding"):
            st.session_state.page = "modding"
    with col2:
        st.markdown("[Discord](https://discord.gg/NBxTbEMznf)", unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "modding"

    if st.session_state.page == "modding":
        st.title("Updated to Standardized 89bb modding")

        uploaded_file = st.file_uploader("Upload 89bb4eb5637df3cd96c463a795005065 file", type=None)
        if uploaded_file:
            if "89bb4eb5637df3cd96c463a795005065" not in uploaded_file.name:
                st.error("Filename must contain '89bb4eb5637df3cd96c463a795005065'")
                return

            file_bytes = uploaded_file.read()
            decrypted_bytes = decrypt_file(file_bytes)

            try:
                _, _, _, _, _, json_data = parse_decrypted_json(decrypted_bytes)
            except Exception as e:
                st.error(f"Failed to parse file: {e}")
                return

            st.markdown("### Select Mod Options")
            max_stars = st.checkbox("Max Stars (Z Power → 9999)")
            zenkai7 = st.checkbox("Zenkai 7 (Awakening Z Power → 7000)")
            max_equips = st.checkbox("Max Equips (Red slots)")
            max_lv_arts = st.checkbox("Max Levels and Arts Boosts")

            if st.button("Modify"):
                updated_json = apply_mods(json_data, max_stars, zenkai7, max_equips, max_lv_arts)
                json_bytes = json.dumps(updated_json, ensure_ascii=False).encode('utf-8')
                encrypted_bytes = encrypt_file(json_bytes)
                buffer = BytesIO(encrypted_bytes)
                st.download_button("Download Modified File", buffer, "89bb4eb5637df3cd96c463a795005065", "application/octet-stream")

if __name__ == "__main__":
    main()
