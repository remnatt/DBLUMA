import json
import os
import pandas as pd
import streamlit as st
from io import BytesIO

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

    # === unitInfo_ (for arts, friendship, and level) ===
    unit_info = data.get("unit", {}).get("unitInfo_", [])
    for unit in unit_info:
        char_id = unit.get("id")

        # Arts boost
        parsed_arts.append({
            "CharID": char_id,
            "strikeArtsBoost": unit.get("strikeArtsBoost", 0),
            "shotArtsBoost": unit.get("shotArtsBoost", 0),
            "specialArtsBoost": unit.get("specialArtsBoost", 0)
        })

        # Friendship level
        parsed_friendship.append({
            "CharID": char_id,
            "friendshipLevel": unit.get("friendshipLevel", 0)
        })

        # Character level
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


def update_data(original_data, edited_chars, edited_equips, edited_arts, edited_friendship, edited_levels):
    # === Update Z Power and Awakening Z Power ===
    for row in edited_chars.itertuples(index=False):
        if row.Category == "Z Power":
            for entry in original_data["item"]["characterShards_"]:
                if entry["characterType"] == row.CharID or (row.CharID == "Shallot" and entry["characterType"] == 9000):
                    entry["count"] = row.Value
        elif row.Category == "Awakening Z Power":
            for entry in original_data["item"]["characterPlentyShards_"]:
                if entry["characterType"] == row.CharID or (row.CharID == "Shallot" and entry["characterType"] == 9000):
                    entry["count"] = row.Value

    # === Update Equip Effects ===
    for row in edited_equips.itertuples(index=False):
        for equip in original_data["item"]["equipItems_"]:
            if equip["equipId"] == row.equipId:
                for ab in equip.get("ability", []):
                    if len(ab.get("ability_effect_param", [])) > 0:
                        try:
                            idx = int(row.Category.replace("Equip Effect [", "").replace("]", ""))
                            ab["ability_effect_param"][idx] = row.Value
                        except Exception:
                            continue

    # === Update Arts Boosts, Friendship Levels, Character Levels ===
    unit_info = original_data.get("unit", {}).get("unitInfo_", [])
    for unit in unit_info:
        for row in edited_arts.itertuples(index=False):
            if unit["id"] == row.CharID:
                unit["strikeArtsBoost"] = min(max(int(row.strikeArtsBoost), 0), 99)
                unit["shotArtsBoost"] = min(max(int(row.shotArtsBoost), 0), 99)
                unit["specialArtsBoost"] = min(max(int(row.specialArtsBoost), 0), 99)

        for row in edited_friendship.itertuples(index=False):
            if unit["id"] == row.CharID:
                unit["friendshipLevel"] = min(max(int(row.friendshipLevel), 0), 15)

        for row in edited_levels.itertuples(index=False):
            if unit["id"] == row.CharID:
                unit["level"] = min(max(int(row.level), 1), 9999)

    return original_data

# === MAIN APP ===

def main():
    st.set_page_config(page_title="DBLUMA | Editor", layout="wide", page_icon="assets/icon.png")
    st.image("assets/banner.png", use_container_width=True)
    st.warning("⚠️ Character Level above 5,000 does NOT work in PvP. Max PvP level is 5,000.")
    st.info("""
    Message from Mindset:
     DBLPS is in the works! Join https://discord.gg/xnnnMpGU8u for more info.   
    """)

    uploaded_file = st.file_uploader("Upload 89bb4eb5637df3cd96c463a795005065 file", type=None)
    if uploaded_file:
        if "89bb4eb5637df3cd96c463a795005065" not in uploaded_file.name:
            st.error("Filename must contain '89bb4eb5637df3cd96c463a795005065'")
            return

        file_bytes = uploaded_file.read()
        decrypted_bytes = decrypt_file(file_bytes)

        try:
            char_df, equip_df, arts_df, friendship_df, level_df, json_data = parse_decrypted_json(decrypted_bytes)
        except Exception as e:
            st.error(f"Failed to parse file: {e}")
            return

        st.success("File parsed successfully! Edit the tables below:")

        st.subheader("Character Z Powers")
        editable_chars = char_df[char_df["Editable"] == True].copy()
        edited_chars = st.data_editor(
            editable_chars[["Category", "CharLabel", "CharID", "Value"]],
            num_rows="dynamic",
            column_config={"CharLabel": st.column_config.TextColumn("Character", disabled=True)},
            key="char_table"
        )

        st.subheader("Equip Effects")
        editable_equips = equip_df[equip_df["Editable"] == True].copy()
        edited_equips = st.data_editor(
            editable_equips[["Category", "equipId", "Value"]],
            num_rows="dynamic",
            key="equip_table"
        )

        st.subheader("Arts Boosts")
        edited_arts = st.data_editor(arts_df, num_rows="dynamic", key="arts_table")

        st.subheader("Friendship Levels")
        edited_friendship = st.data_editor(friendship_df, num_rows="dynamic", key="friend_table")

        st.subheader("Character Levels")
        edited_levels = st.data_editor(level_df, num_rows="dynamic", key="level_table")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Download Edited CSVs"):
                st.download_button("Download Character CSV", edited_chars.to_csv(index=False).encode("utf-8"), "edited_characters.csv", "text/csv")
                st.download_button("Download Equip CSV", edited_equips.to_csv(index=False).encode("utf-8"), "edited_equips.csv", "text/csv")
                st.download_button("Download Arts Boost CSV", edited_arts.to_csv(index=False).encode("utf-8"), "edited_arts_boosts.csv", "text/csv")
                st.download_button("Download Friendship CSV", edited_friendship.to_csv(index=False).encode("utf-8"), "edited_friendship.csv", "text/csv")
                st.download_button("Download Levels CSV", edited_levels.to_csv(index=False).encode("utf-8"), "edited_levels.csv", "text/csv")

        with col2:
            if st.button("Download Re-encrypted File"):
                updated_json = update_data(json_data, edited_chars, edited_equips, edited_arts, edited_friendship, edited_levels)
                json_bytes = json.dumps(updated_json, ensure_ascii=False).encode('utf-8')
                encrypted_bytes = encrypt_file(json_bytes)
                buffer = BytesIO(encrypted_bytes)
                st.download_button("Download Encrypted File", buffer, "89bb4eb5637df3cd96c463a795005065", "application/octet-stream")

if __name__ == "__main__":
    main()
