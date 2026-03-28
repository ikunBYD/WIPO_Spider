import re
import requests
import execjs
from bs4 import BeautifulSoup
import os
import base64
from model import recognize_image

BASE_URL = 'https://patentscope.wipo.int'
js_path = r'piwik_.js'   # 确保此文件存在


def get_ori_cookie():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://patentscope.wipo.int",
    }

    resp = requests.get(BASE_URL + '/search/en/search.jsf', headers=headers)
    cookie = resp.headers.get('Set-Cookie', '')

    os.environ["EXECJS_RUNTIME"] = "PhantomJS"
    ctx = execjs.compile(open(js_path, "r", encoding="utf-8").read())
    params = ctx.eval('asdfg()')

    cookie = f'{cookie}; _pk_ses.5.5313=1; _pk_id.5.5313={params}'
    print("初始 cookie:", cookie)

    return cookie
# 检查验证码是否被打穿
def check(headers):
    resp = requests.get(BASE_URL + '/search/en/search.jsf', headers=headers)
    soup = BeautifulSoup(resp.content, "lxml")
    qt_div = soup.find('div', class_='b-view-panel__section')
    if qt_div is not None:
        return False
    return True

def get_captcha_info(headers):
    resp = requests.get(BASE_URL + '/search/en/search.jsf', headers=headers)
    soup = BeautifulSoup(resp.content, "lxml")

    viewstate_match = re.search(
        r'name="javax\.faces\.ViewState".*?value="([^"]+)"',
        resp.text
    )
    viewstate = viewstate_match.group(1) if viewstate_match else ""

    qt_div = soup.find('div', class_='b-view-panel__section')
    if qt_div:
        question_text = qt_div.get_text().strip().replace(' ', '_')
    else:
        question_text = ""

    img_urls = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and "base64" in src:
            img_urls.append(src)

    return viewstate, question_text, img_urls


def download_image(base64_str, save_path):
    try:
        base64_data = base64_str.split("base64,")[-1]

        # padding 修复
        base64_data += "=" * (-len(base64_data) % 4)

        img_bytes = base64.b64decode(base64_data)

        with open("captcha/"+save_path, "wb") as f:
            f.write(img_bytes)

        print(f"✅ 保存成功: {save_path}")

    except Exception as e:
        print(f"❌ 保存失败: {e}")


def spider_gun():
    # 1. 获取 cookie
    cookie = get_ori_cookie()

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Cookie': cookie
    }

    # 2. 获取验证码
    viewstate, question, image_urls = get_captcha_info(headers)

    print("问题:", question)

    if not image_urls:
        print("❌ 没有获取到验证码")
        return False,None,None

    # 3. 下载全部验证码图片
    for idx, img_base64 in enumerate(image_urls):
        save_name = f"captcha_{idx}.png"
        download_image(img_base64, save_name)

    print("✅ 所有验证码已保存完成")
    print("准备调用模型进行分析")
    keyword=question.split("_")[-1]
    model_result=[]
    for pict in os.listdir(f"captcha/"):

        quest=f"If the image mainly contains {keyword}, return 1; otherwise, return 0. Follow the requirement strictly."
        result=recognize_image(f"captcha/{pict}", quest)
        model_result.append(result)
        # 提前弹出避免浪费
        if int(result)>0:
            break

    if "1" not in model_result:
        print("模型判断失败准备重新请求")
    else:
        print("判断成功准备模拟请求")
        check_number=model_result.index("1")+1
        payload={
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": f"click{check_number}",
        "javax.faces.partial.execute": "@all",
        "javax.faces.partial.render": "psCaptchaPanel",
        f"click{check_number}": f"click{check_number}",
        "psCaptchaForm": "psCaptchaForm",
        "javax.faces.ViewState": viewstate,
        }
        req = requests.post("https://patentscope.wipo.int/search/en/search.jsf", headers=headers, data=payload)

        if check(headers):
            return True,viewstate,cookie
        else:
            return False,None,None
    return viewstate, question, image_urls, headers


if __name__ == '__main__':
    main()