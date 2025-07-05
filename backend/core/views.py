import base64
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI

LAOZHANG_API_KEYS = [
    "sk-JRtt6ZJ1QFvigS3G56FdB74bEcEc435493Bd32E9C34466De", # hoh873700
]

layout_prompt = '''請對這張住宅平面圖進行詳細分析，包括但不限於以下幾點：

- 各個區域的功能，例如大門、玄關、客廳、餐廳、廚房、主臥室、次臥室、客臥室、浴室、前陽台、後陽台等的位置。
- 是否有任何結構樑或其他結構上的限制，例如:壓樑。並請標示其位置。
- 浴室是否有對外窗或通風設施。
- 客廳、餐廳、廚房、主臥室、次臥室、客臥室是否有對外窗。
- 房間的配置與動線是否合理，是否有任何不尋常或不適當之處。
- 根據平面圖，是否還有其他家具配置或使用建議。

請以清楚的條列式格式回答，並說明你做出判斷的依據以及每個空間的位置。
'''
def get_house_layout_from_img_url(layout_prompt, image_url, is_simulate=True):
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

    base_url = "https://api.laozhang.ai/v1"
    for key in LAOZHANG_API_KEYS:
          try:
              client = OpenAI(api_key=key, base_url=base_url)
              response = client.responses.create(
                  model="gpt-4.1-mini",
                  input=[{
                      "role": "user",
                      "content": [
                          {"type": "input_text", "text": layout_prompt},
                          {
                              "type": "input_image",
                              "image_url": image_url,
                          },
                      ],
                  }],
              )
              return response.output_text

          except Exception as e:
              print(f"[!] API key 失敗：{key[:10]}...，錯誤：{e}")
              continue

    return ""

def generate_prompt(house_layout: str, items: list[str]) -> str:
    item_list = "\n".join(f"- {item}" for item in items)

    prompt = f"""請根據以下的房屋格局描述，判斷是否符合使用者在意的每一個看房項目。
對於每一個項目，請給出 ✅（符合）或 ❌（不符合），並提供簡要的原因說明。

房屋格局描述（house_layout）：
{house_layout}

使用者在意的項目（items）：
{item_list}

請以以下格式回覆：

1. {{項目名稱}}：✅ / ❌  
   說明原因：為什麼符合或不符合
"""
    return prompt

def chat_with_laozhang(messages, model="deepseek-v3"):
    base_url = "https://api.laozhang.ai/v1"

    for key in LAOZHANG_API_KEYS:
        try:
            client = OpenAI(api_key=key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"[!] API key 失敗：{key[:10]}...，錯誤：{e}")
            continue

    return "OpenAI 額度用完了 QQ"

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
            # TODO: 前端傳 base64 圖片（data URL 格式）
            print("[INFO] handling image data")
        elif image_url:
            # 從網址抓圖片
            print("[INFO] handling image_url: " + image_url)
            house_layout = get_house_layout_from_img_url(layout_prompt, image_url)
            if not house_layout:
                return JsonResponse({"error": "分析房屋格局發生錯誤"}, status=400)
            print(house_layout)
        else:
            return JsonResponse({"error": "Missing image data or image URL"}, status=400)

        for item in items:
            print(item)

        prompt = generate_prompt(house_layout, items)
        print(prompt)
        messages=[
            {"role": "system", "content": "你是一個中文房屋格局分析專家"},
            {"role": "user", "content": prompt}
        ]
        result = chat_with_laozhang(messages)
        print(result)
        return JsonResponse({"result": result})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
