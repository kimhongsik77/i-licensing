#!/usr/bin/env python3
"""HÖRU 작업 품목 마스터 생성 — 공식 17개 카테고리(브랜드소개서 Type3) → 패션/패션잡화/라이프스타일 3대분류
출력: catalog/product_master.yaml (시스템용 원본) + catalog/product_master.csv (시트·검토용)
수정은 이 파일의 ITEMS 표에서 한 뒤 다시 실행: python3 horu-lookbook/catalog/build_catalog.py
"""
import csv, sys
from pathlib import Path
import yaml

OUT = Path(__file__).resolve().parent
# 카테고리 기본값: 대분류, 공식명, 코드, 단계, 매칭기 유형 기본, 벤치마크(글로벌/국내), 로고 1순위, 슬로건 상황, 촬영, 기존 실사 폴더
CATS = {
 "ATH": ("패션", "Athleisure", 1, "lululemon / 안다르", "왼가슴 조합로고 반사 + 허리밴드 뒤 텍스트로고", "active_apparel(MAIN)", "착장", "Fashion/Athleisure & Gymwear, OLD/에스레저"),
 "YC":  ("패션", "Young Casual", 1, "Uniqlo / 무신사 스탠다드", "왼가슴 톤온톤 소형 자수 + 넥 라벨·헴 플래그", "casual_apparel(SUB_A)", "착장", "-"),
 "GLF": ("패션", "Golf Wear", 2, "미선정(공식평가 기준 선정 필요)", "왼가슴 자수 + 소매 텍스트로고", "active_apparel(MAIN)", "착장", "golf, OLD/골프"),
 "TEN": ("패션", "Tennis Wear", 2, "미선정", "왼가슴 자수 + 스커트 허리 텍스트로고", "active_apparel(MAIN)", "착장", "OLD/테니스"),
 "OUT": ("패션", "Outdoor", 2, "미선정", "왼가슴 반사/실리콘 + 소매 세로 슬로건", "active_apparel(MAIN)", "착장", "Fashion/outdoor, OLD/아웃도어"),
 "CYC": ("패션", "Cycling Wear", 3, "미선정", "옆선 반사 텍스트로고 + 뒷목", "active_apparel(MAIN)", "착장", "Fashion/cycle, OLD/사이클"),
 "SWM": ("패션", "Swimwear", 3, "미선정", "허리·가슴 소형 실리콘 텍스트로고", "active_apparel(MAIN)", "착장", "-"),
 "FSH": ("패션", "Fishing Wear", 3, "미선정", "왼가슴 러버 패치", "active_apparel(MAIN)", "착장", "-"),
 "KID": ("패션", "Kids (공식 17개 외 후보)", 3, "미선정", "왼가슴 자수", "casual_apparel(SUB_A)", "착장(키즈 모델 기준 없음)", "Fashion/KIDS"),
 "BAG": ("패션잡화", "Bag", 1, "JanSport / 살로몬 Trailblazer", "전면 상단 패치 + 스트랩 우븐 테이프", "bag(MAIN)", "누끼+착장", "Bag, bag, OLD/여행용가방"),
 "CAP": ("패션잡화", "Hats & Caps", 1, "New Era / 이미스", "정면 조합로고 자수 + 측면 텍스트로고", "cap(SUB_B)", "누끼+착장", "-"),
 "EYE": ("패션잡화", "Sunglasses", 2, "미선정", "템플 각인 텍스트로고", "campaign_call(SUB_B)", "누끼+착장", "-"),
 "ACC": ("패션잡화", "Accessories (Watch 등)", 3, "미선정", "다이얼·스트랩 각인", "campaign_call(SUB_B)", "누끼", "-"),
 "SGD": ("패션잡화", "Sports Goods (장갑·양말·헬멧 등)", 2, "미선정", "손등·발목 소형 텍스트로고", "active_apparel(MAIN)", "누끼", "OLD/사이클, golf"),
 "KIT": ("라이프스타일", "Kitchenware (드링크웨어 포함)", 1, "Stanley / 써모스 코리아", "몸통 정면 조합로고 + 반대면 각인", "drinkware(SUB_B)", "누끼+연출", "-"),
 "CMP": ("라이프스타일", "Camping & Leisure", 2, "미선정", "원단 라벨·본체 프린트", "drinkware(SUB_B)", "연출", "Fashion/camping"),
 "HOM": ("라이프스타일", "Home & Bedding", 3, "미선정", "모서리 우븐 라벨", "editorial_story(SUB_A)", "연출", "-"),
 "DSK": ("라이프스타일", "Desk Items", 3, "미선정", "정면 각인·형압", "editorial_story(SUB_A)", "누끼+연출", "-"),
 "DEC": ("라이프스타일", "Small Furniture & Decor", 3, "미선정", "하단 각인·라벨", "editorial_story(SUB_A)", "연출", "-"),
}
# (카테고리, 품목명, 영문, 매칭기 유형, 비고)
ITEMS = [
 ("ATH","레깅스","Leggings","bottom",""),("ATH","조거 팬츠","Jogger Pants","bottom",""),
 ("ATH","스포츠 브라·크롭탑","Sports Bra / Crop Top","top",""),("ATH","기능성 반팔 티","Performance Tee","top",""),
 ("ATH","하프집업 풀오버","Half-zip Pullover","top",""),("ATH","바람막이 재킷","Windbreaker","top","SS27 p8 착장 존재"),
 ("ATH","트레이닝 쇼츠","Training Shorts","bottom",""),
 ("YC","오버핏 반팔 티","Oversized Tee","top","SS27 p1~3 착장 존재"),("YC","맨투맨","Sweatshirt","top","SS27 p4~6 착장 존재"),
 ("YC","후디","Hoodie","top",""),("YC","니트 가디건","Knit Cardigan","top","SS27 p7 착장 존재"),
 ("YC","커브드 치노 팬츠","Curved Chino Pants","bottom","국내 트렌드(검색 3.4배)"),("YC","와이드 팬츠","Wide Pants","bottom","SS27 착장 존재"),
 ("YC","셔츠","Shirt","top",""),
 ("GLF","폴로 셔츠","Polo Shirt","top",""),("GLF","골프 하프집업","Golf Half-zip","top",""),("GLF","골프 팬츠","Golf Pants","bottom",""),
 ("GLF","플리츠 스커트","Pleated Skirt","bottom",""),("GLF","니트 베스트","Knit Vest","top",""),
 ("TEN","테니스 티·폴로","Tennis Tee / Polo","top",""),("TEN","테니스 스커트","Tennis Skirt","bottom",""),
 ("TEN","테니스 쇼츠","Tennis Shorts","bottom",""),("TEN","집업 재킷","Track Jacket","top",""),
 ("OUT","방수 쉘 재킷","Waterproof Shell","top",""),("OUT","경량 패딩","Light Down Jacket","top",""),
 ("OUT","플리스 재킷","Fleece Jacket","top",""),("OUT","트레킹 팬츠","Trekking Pants","bottom",""),
 ("CYC","사이클 저지","Cycling Jersey","top",""),("CYC","빕숏","Bib Shorts","bottom",""),
 ("SWM","원피스 수영복","One-piece Swimsuit","top","유형 근사(top) — 전용 배치 필요"),("SWM","래시가드","Rash Guard","top",""),
 ("SWM","보드쇼츠","Board Shorts","bottom",""),
 ("FSH","피싱 베스트","Fishing Vest","top",""),("FSH","기능성 후디","UV Hoodie","top",""),
 ("KID","키즈 맨투맨","Kids Sweatshirt","top","키즈 모델 기준 결정 필요"),("KID","키즈 바람막이","Kids Windbreaker","top","키즈 모델 기준 결정 필요"),
 ("BAG","데이팩 백팩","Daypack","bag",""),("BAG","슬링백","Sling Bag","bag",""),("BAG","토트백","Tote Bag","bag",""),
 ("BAG","더플백","Duffel Bag","bag",""),("BAG","여행용 캐리어","Luggage","goods","전용 배치 필요"),
 ("CAP","볼캡","Ball Cap","cap",""),("CAP","러닝캡","Running Cap","cap",""),("CAP","버킷햇","Bucket Hat","cap","유형 근사(cap)"),
 ("CAP","비니","Beanie","beanie",""),
 ("EYE","스포츠 선글라스","Sport Sunglasses","goods",""),("EYE","라이프스타일 선글라스","Lifestyle Sunglasses","goods",""),
 ("ACC","스포츠 워치","Sport Watch","goods",""),("ACC","워치 스트랩","Watch Strap","goods",""),
 ("SGD","스포츠 양말","Sport Socks","goods",""),("SGD","골프 장갑","Golf Glove","goods","기존 AI 이미지 깨진 텍스트로 제외 이력"),
 ("SGD","사이클 헬멧","Cycling Helmet","goods",""),("SGD","사이클 장갑","Cycling Gloves","goods",""),
 ("SGD","골프백","Golf Bag","bag",""),("SGD","헤어밴드·손목밴드","Head/Wrist Band","goods",""),
 ("KIT","텀블러","Tumbler","tumbler",""),("KIT","보틀","Water Bottle","tumbler",""),("KIT","머그","Mug","tumbler","유형 근사(tumbler)"),
 ("KIT","식기 세트","Tableware Set","goods",""),("KIT","보관용기","Storage Container","goods",""),
 ("CMP","캠핑 체어","Camping Chair","goods",""),("CMP","텐트·타프","Tent / Tarp","goods",""),("CMP","랜턴","Lantern","goods",""),
 ("CMP","캠핑 쿡웨어","Camping Cookware","goods","기존 '주방' 이미지 경쟁사 문구 제외 이력"),
 ("HOM","침구 세트","Bedding Set","goods","기존 침구매장 이미지 문구 크롭 이력"),("HOM","블랭킷","Throw Blanket","goods",""),("HOM","쿠션","Cushion","goods",""),
 ("DSK","데스크 매트·오거나이저","Desk Mat & Organizer","goods","소개서 제안 라인업"),("DSK","원목 데스크 트레이","Wood Desk Tray","goods","소개서 제안 라인업"),
 ("DSK","다이어리·문구 세트","Diary & Stationery","goods","소개서 제안 라인업"),("DSK","노트북 스탠드","Laptop Stand","goods","소개서 제안 라인업"),
 ("DSK","리필 스틸 텀블러","Refill Steel Tumbler","tumbler","소개서 제안 라인업"),
 ("DEC","무드등·캔들","Mood Lamp & Candle","goods","소개서 제안 라인업"),("DEC","오브제 트레이","Object Tray","goods","소개서 제안 라인업"),
 ("DEC","미니 플랜터","Mini Planter","goods","소개서 제안 라인업"),("DEC","리넨 쿠션·블랭킷","Linen Cushion & Throw","goods","소개서 제안 라인업"),
 ("DEC","사이드 테이블","Side Table","goods","소개서 제안 라인업"),
]
MODEL = {"P1": "VM-F-EA01, VM-M-EA01, VM-F-NE01, VM-M-NE01"}
ITEM_OVERRIDE = {  # 품목명: (벤치마크, 로고 기본 적용) — None이면 카테고리 기본값 유지
 "식기 세트": ("미선정", "접시 뒷면 형압·하단 각인"),
 "보관용기": ("미선정", "뚜껑 형압 + 측면 소형 프린트"),
 "골프백": ("미선정", "전면 포켓 러버 패치 + 스트랩 텍스트로고"),
 "여행용 캐리어": (None, "전면 상단 러버 패치 + 손잡이 텍스트로고"),
 "사이클 헬멧": (None, "측면 반사 텍스트로고"),
 "스포츠 양말": (None, "발목 자카드 텍스트로고"),
 "헤어밴드·손목밴드": (None, "정면 실리콘 텍스트로고"),
 "비니": (None, "커프 정면 가죽·우븐 패치 (조합로고)"),
}
BOTTOM_LOGO = {   # 하의는 가슴이 없으므로 카테고리별 하의 전용 위치 (logo_placement_library bottom 기준)
 "ATH": "허리밴드 뒤 텍스트로고(실리콘) + 왼쪽 엉덩이 반사",
 "YC": "뒤 허리 우븐 라벨 + 뒷주머니 소형 자수",
 "GLF": "뒤 허리 텍스트로고 + 왼쪽 엉덩이 소형 자수",
 "TEN": "허리 텍스트로고 프린트",
 "OUT": "왼쪽 허벅지 반사 텍스트로고",
 "CYC": "허벅지 옆선 반사 텍스트로고",
 "SWM": "허리 소형 실리콘 텍스트로고",
}

rows, counters = [], {}
for cat, name, en, mtype, note in ITEMS:
    big, cname, phase, bench, logo, slogan, shoot, assets = CATS[cat]
    counters[cat] = counters.get(cat, 0) + 1
    big_code = {"패션": "FA", "패션잡화": "AC", "라이프스타일": "LS"}[big]
    model = MODEL["P1"] if ("착장" in shoot and cat != "KID") else ("키즈 기준 미정" if cat == "KID" else "-")
    if mtype == "bottom" and cat in BOTTOM_LOGO:
        logo = BOTTOM_LOGO[cat]
    if mtype == "top" and cat == "ATH":
        logo = "왼가슴 조합로고 반사 + 뒷목 MAIN 슬로건 프린트"
    if mtype == "top" and cat == "TEN":
        logo = "왼가슴 조합로고 자수 + 소매 텍스트로고"
    for key, (b2, l2) in ITEM_OVERRIDE.items():          # 품목 단위 예외 (카테고리 기본값과 다른 품목)
        if key == name:
            bench, logo = b2 or bench, l2 or logo
    rows.append({"품목ID": f"{big_code}-{cat}-{counters[cat]:03d}", "대분류": big, "카테고리": cname, "품목명": name,
                 "영문명": en, "매칭기유형": mtype, "단계": f"Phase {phase}", "벤치마크(글로벌/국내)": bench,
                 "로고 기본 적용": logo, "슬로건 상황": slogan, "촬영 방식": shoot, "추천 모델": model,
                 "기존 실사 폴더": assets, "상태": "대기", "비고": note})
(OUT / "product_master.yaml").write_text(yaml.safe_dump({"source": "브랜드소개서 Type3 공식 17개 카테고리 + Drive Product 폴더 (2026-11-20)",
                                                          "items": rows}, allow_unicode=True, sort_keys=False), encoding="utf-8")
with open(OUT / "product_master.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
from collections import Counter
c = Counter((r["대분류"], r["단계"]) for r in rows)
print(f"품목 {len(rows)}개 / 카테고리 {len(CATS)}개")
for big in ("패션", "패션잡화", "라이프스타일"):
    print(big, {p: c[(big, p)] for p in ("Phase 1", "Phase 2", "Phase 3")})
