import asyncio
import edge_tts

async def list_all_vietnamese_voices():
    voices = await edge_tts.VoicesManager.create()
    all_voices = voices.voices
    
    vi_voices = [v for v in all_voices if "vietnam" in v["FriendlyName"].lower() or "vi-VN" in v["ShortName"]]
    
    print("=== DANH SÁCH GIỌNG ĐỌC TIẾNG VIỆT (TẤT CẢ) ===")
    if not vi_voices:
        print("Không tìm thấy giọng đọc tiếng Việt nào.")
    for v in vi_voices:
        gender = "Nữ" if v["Gender"] == "Female" else "Nam"
        print(f"ID: {v['ShortName']}")
        print(f"Tên: {v['FriendlyName']}")
        print(f"Giới tính: {gender}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(list_all_vietnamese_voices())
