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

    # === characterShards_ ===
    shards = data.get("item", {}).get("characterShards_", [])
    for entry in shards:
        char_id = entry.get("characterType")
        char_name = "Shallot" if char_id == 9000 else char_id
        parsed_chars.append({
            "Category": "Z Power",
            "CharID": char_name,
            "Value": entry.get("count"),
            "Editable": True
        })

    # === characterPlentyShards_ ===
    plenty = data.get("item", {}).get("characterPlentyShards_", [])
    for entry in plenty:
        char_id = entry.get("characterType")
        char_name = "Shallot" if char_id == 9000 else char_id
        parsed_chars.append({
            "Category": "Awakening Z Power",
            "CharID": char_name,
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

    return pd.DataFrame(parsed_chars), pd.DataFrame(parsed_equips), data

def update_data(original_data, edited_chars, edited_equips):
    # === Update characters ===
    for row in edited_chars.itertuples(index=False):
        if row.Category == "Z Power":
            for entry in original_data["item"]["characterShards_"]:
                if entry["characterType"] == row.CharID or (row.CharID == "Shallot" and entry["characterType"] == 9000):
                    entry["count"] = row.Value
        elif row.Category == "Awakening Z Power":
            for entry in original_data["item"]["characterPlentyShards_"]:
                if entry["characterType"] == row.CharID or (row.CharID == "Shallot" and entry["characterType"] == 9000):
                    entry["count"] = row.Value

    # === Update equips ===
    for row in edited_equips.itertuples(index=False):
        for equip in original_data["item"]["equipItems_"]:
            if equip["equipId"] == row.equipId:
                for ab in equip.get("ability", []):
                    if len(ab["ability_effect_param"]) > 0:
                        try:
                            idx = int(row.Category.replace("Equip Effect [", "").replace("]", ""))
                            ab["ability_effect_param"][idx] = row.Value
                        except Exception:
                            continue
    return original_data

# === MAIN APP ===

def main():
    st.set_page_config(page_title="DBLUMA | Editor", layout="wide", page_icon="assets/icon.png")
    st.image("assets/banner.png", use_container_width=True)
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
            char_df, equip_df, json_data = parse_decrypted_json(decrypted_bytes)
        except Exception as e:
            st.error(f"Failed to parse file: {e}")
            return

        st.success("File parsed successfully! Edit the tables below:")

        # === Editable Character Table ===
        st.subheader("Character Z Powers")
        editable_chars = char_df[char_df["Editable"] == True].copy()
        edited_chars = st.data_editor(editable_chars[["Category", "CharID", "Value"]], num_rows="dynamic", key="char_table")

        # === Editable Equip Table ===
        st.subheader("Equip Effects")
        editable_equips = equip_df[equip_df["Editable"] == True].copy()
        edited_equips = st.data_editor(editable_equips[["Category", "equipId", "Value"]], num_rows="dynamic", key="equip_table")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Download Edited CSVs"):
                chars_csv = edited_chars.to_csv(index=False).encode("utf-8")
                equips_csv = edited_equips.to_csv(index=False).encode("utf-8")
                st.download_button("Download Character CSV", chars_csv, "edited_characters.csv", "text/csv")
                st.download_button("Download Equip CSV", equips_csv, "edited_equips.csv", "text/csv")

        with col2:
            if st.button("Download Re-encrypted File"):
                updated_json = update_data(json_data, edited_chars, edited_equips)
                json_bytes = json.dumps(updated_json, ensure_ascii=False).encode('utf-8')
                encrypted_bytes = encrypt_file(json_bytes)
                buffer = BytesIO(encrypted_bytes)
                st.download_button("Download Encrypted File", buffer, "89bb4eb5637df3cd96c463a795005065", "application/octet-stream")

if __name__ == "__main__":
    main()
