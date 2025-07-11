import base64
import json
import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI


# https://api.imgbb.com/
IMGBB_API_KEYS = [
    "d714308471b48b4a0668d1245e6fe36c", # llvmphighter
    "02bd7ddf10b4c5bb30a6c6aafcb1e2ac", # j199180305
]
def upload_to_imgbb(image_data):
    for key in IMGBB_API_KEYS:
        try:
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": key,
                "image": image_data
            }
            response = requests.post(url, data=payload)

            if response.status_code == 200:
                data = response.json()
                return data["data"]["url"]  # 取得圖片網址
            else:
                print("KEY is not valid: " + key)
                continue
        except Exception as e:
            print("KEY is not valid: " + key)
            continue
    print("[ERROR]: 所有key都失敗")
    return None


LAOZHANG_API_KEYS = [
    "sk-adwTZ7MUxpICWiaT717d71E086E54161904a1eAb82682dCf", # hoh873700
    "sk-JRtt6ZJ1QFvigS3G56FdB74bEcEc435493Bd32E9C34466De", # woyang84
    "sk-mzDhgswG4QXbDtMBE73fBeBb2d974050B7D1Ec4a0fBc795c", # laozhang1323, gmail: laozhanglas
    "sk-ZBH1AXcWEWEOhMCiA4813d3818Cc433e9c140618A5Ed5dD1", # qq132132
    "sk-9ku03D7e746VE0JTDcCfCe53C90842D98b197288835aD135", # jason456456
]

system_prompt = '''
你是一位專業的房屋格局分析師，請根據圖片內容協助判斷格局用途。
你的背景知識:
1. 窗戶可能 #白框# 或 #白框內有平行細黑線# 的形式出現，如果外牆是黑心實線則表示沒有窗戶。
2. 樑通常是 #兩根黑柱連結包含的區域#。如果此區域與床頭重疊的話，則代表床頭壓樑。
3. 如果有指北針或指南針，則可以判斷方位。若沒有，則回覆無法判斷方位。
4. 判斷房屋座向，可以站在房屋內部面向大門或主要採光面（如陽台或落地窗），背對的方向即為「坐向」，而面向的方向則為「朝向」。 
例如，背對南方，面向北方，則為坐南朝北。
5. 廚房和浴室如果在房屋的正中間，不良的氣味容易沿著管線散佈到周圍其他房間
'''
def generate_layout_prompt(items: list[str]) -> str:
    item_list = "\n".join(f"- {item}" for item in items)

    prompt = f"""請對這張住宅平面圖進行以下詳細分析，判斷是否符合使用者在意的每一個看房項目。
對於每一個項目，請給出 （是）或（否），並提供簡要的原因說明。

使用者在意的項目（items）：
{item_list}

請以以下格式回覆：

整體房屋格局，例如客廳 餐廳 廚房 浴室 房間分別在哪裡
接著才以使用者在意的看房項目回覆，顯示時要說: ✏️您所關心的項目

{{項目名稱}}：
   說明原因：為什麼符合或不符合

請不要使用 ** 或 Markdown 粗體符號。
"""
    return prompt

def get_house_layout_from_img_url(items, image_url, is_simulate=False):
    if is_simulate:
        return '''
          1. 各區域功能與位置：
  - 大門：位於圖下方中間位置，開門進入後直接面向客廳區。
  - 客廳：位於入口右側下方，配置L型沙發與茶几，地毯上有英國國旗圖案。
  - 餐廳：位於入口左側中央位置，靠近廚房，設有餐桌與兩張椅子。
  - 廚房：在圖左下角，封閉式空間並有廚具設備與工作檯面。
  - 臥室：有兩間臥室
    - 左上方臥室：擺放雙人床、床頭櫃及衣櫃。
    - 右上方臥室：擺放雙人床、床頭櫃及衣櫃，且緊鄰浴室。
  - 浴室：位於右中央，緊鄰右側臥室，設有淋浴區、馬桶和洗手台。

2. 結構樑或其他結構限制：
  - 由圖中黑色粗邊線可判斷為結構牆體，尤其靠牆面的兩側及中間分隔牆較厚，代表結構承重牆。
  - 中間仕切牆兩側的雙臥室牆面可能也是結構牆或加強牆。
  - 沒有顯示明顯橫樑標示，推斷結構限制主要在黑色粗牆及幾個較厚的牆面。

3. 浴室通風與採光：
  - 浴室位於最右側中央且有向右側開設窗戶，且窗戶外面似乎為陽台或空間，因此具備對外窗戶與通風設施。
  - 此窗戶有利於浴室除濕與空氣流通。

4. 房間配置與動線合理性：
  - 入口直接面對客廳，動線順暢，餐廳與廚房連接良好，使用方便。
  - 兩臥室互相靠近，且分隔牆上有合理動線，且臥室進出門分別配置良好。
  - 公共空間（客廳、餐廳、廚房）集中於左圈與中心區域，私密空間則配置於上方較隱密處。
  - 唯一較小疑問為左側臥室的床尾與衣櫃中間空間較窄，行走動線可能受限，但大致合理。

總結判斷皆是根據圖中家具擺設、門窗位置、結構牆線條、以及空間動線邏輯綜合分析得出。此平面圖整體設計合理且實用。
'''
    print("[INFO] Analyzing " + image_url)
    layout_prompt = generate_layout_prompt(items)
    base_url = "https://api.laozhang.ai/v1"
    for key in LAOZHANG_API_KEYS:
          try:
              client = OpenAI(api_key=key, base_url=base_url)
              response = client.responses.create(
                  model="gpt-4o",
                  input=[
                        {
                            "role": "system",
                            "content": (
                                "你是一位專業的房屋格局分析師，請根據圖片內容協助判斷格局用途。"
                                "特別要注意：請詳細觀察哪些區域的外牆有窗戶，窗戶可能以長條線、白框或平行標記出現，如果外牆是黑心實線則表示沒有窗戶。樑通常是兩根黑柱連結包含的區域。"
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": layout_prompt},
                                {
                                    "type": "input_image",
                                    "image_url": image_url,
                                },
                            ],
                        }
                  ],
              )
              return response.output_text

          except Exception as e:
              print(f"[!] API key 失敗：{key[:10]}...，錯誤：{e}")
              continue

    return ""

def home(request):
    return render(request, 'home.html')

@csrf_exempt
def analyze_layout(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        body = json.loads(request.body)
        image_data = body.get("image")        # base64 圖片字串 (data URL)
        image_url = body.get("image_url")     # 圖片網址
        items = body.get("items", [])

        if not items:
            return JsonResponse({"error": "Missing items"}, status=400)

        image_binary = None

        house_layout = ""
        if image_data:
            print("[INFO] handling image data")
            if image_data.startswith("data:image"):
                image_data = image_data.split(",")[1]
            image_url = upload_to_imgbb(image_data)

        if not image_url:
            print("[ERROR]: handling image data fails")
            return JsonResponse({"error": "分析房屋格局發生錯誤"}, status=400)

        house_layout = get_house_layout_from_img_url(items, image_url)
        if not house_layout:
            return JsonResponse({"error": "分析房屋格局發生錯誤"}, status=400)
        print(house_layout)
        return JsonResponse({"result": house_layout})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
