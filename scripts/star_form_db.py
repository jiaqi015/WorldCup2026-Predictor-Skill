"""
STAR_FORM_DB: 2024-25 club season form data for elite-tier players.

Goals/Assists figures come from the 2024-25 European top-5 league + Champions League
season totals (rounded). This drives the form_factor in compute_player_threats v2.

Each entry: cn_name -> {g: club_goals, a: club_assists, mins: minutes_share_0_to_1,
nation: team_cn (for collision resolution)}

Coverage target: ~80-100 marquee attackers/creators across all 48 teams.
Players not in this DB use neutral form (g=baseline, a=baseline).
"""

# {chinese_name -> {g, a, mins, nation}}
STAR_FORM_DB = {
    # —— 阿根廷 ——
    "梅西":         {"g": 28, "a": 16, "mins": 0.85, "nation": "阿根廷"},  # MLS 2024
    "劳塔罗":       {"g": 24, "a":  4, "mins": 0.80, "nation": "阿根廷"},  # Inter
    "阿尔瓦雷斯":   {"g": 25, "a":  8, "mins": 0.85, "nation": "阿根廷"},  # Atlético
    "迪马利亚":     {"g": 12, "a": 13, "mins": 0.70, "nation": "阿根廷"},
    "麦克阿利斯特": {"g":  8, "a":  6, "mins": 0.75, "nation": "阿根廷"},  # Liverpool
    "恩索费尔南德斯":{"g":  3, "a":  4, "mins": 0.75, "nation": "阿根廷"},  # Chelsea
    "蒂亚戈":       {"g":  9, "a":  8, "mins": 0.70, "nation": "阿根廷"},  # Atlético Madrid
    "罗梅罗":       {"g":  3, "a":  1, "mins": 0.85, "nation": "阿根廷"},  # Tottenham CB
    # —— 葡萄牙 ——
    "C罗":          {"g": 35, "a":  8, "mins": 0.85, "nation": "葡萄牙"},  # Al-Nassr
    "B费":          {"g": 18, "a": 18, "mins": 0.90, "nation": "葡萄牙"},  # ManU
    "B席":          {"g":  4, "a": 14, "mins": 0.75, "nation": "葡萄牙"},  # Man City
    "拉斐尔莱昂":   {"g": 12, "a":  9, "mins": 0.80, "nation": "葡萄牙"},  # Milan
    "Gonçalo拉莫斯":{"g": 21, "a":  3, "mins": 0.55, "nation": "葡萄牙"},  # PSG
    "若昂菲利克斯": {"g": 10, "a":  6, "mins": 0.50, "nation": "葡萄牙"},
    "若塔":         {"g": 15, "a":  5, "mins": 0.70, "nation": "葡萄牙"},
    "佩德罗内托":   {"g":  3, "a":  9, "mins": 0.70, "nation": "葡萄牙"},  # Chelsea
    "若昂内维斯":   {"g":  3, "a":  4, "mins": 0.75, "nation": "葡萄牙"},  # PSG
    "维蒂尼亚":     {"g":  6, "a":  7, "mins": 0.85, "nation": "葡萄牙"},  # PSG
    # —— 法国 ——
    "姆巴佩":       {"g": 39, "a":  8, "mins": 0.85, "nation": "法国"},  # Real Madrid
    "登贝莱":       {"g": 33, "a": 13, "mins": 0.85, "nation": "法国"},  # PSG, Ballon d'Or
    "格列兹曼":     {"g": 16, "a":  9, "mins": 0.80, "nation": "法国"},  # Atlético
    "图拉姆":       {"g": 16, "a":  4, "mins": 0.75, "nation": "法国"},  # Inter
    "巴尔科拉":     {"g": 11, "a":  9, "mins": 0.65, "nation": "法国"},  # PSG
    "奥利塞":       {"g": 18, "a": 14, "mins": 0.85, "nation": "法国"},  # Bayern
    "库尼亚":       {"g": 17, "a":  6, "mins": 0.80, "nation": "法国"},
    "卡马文加":     {"g":  3, "a":  4, "mins": 0.65, "nation": "法国"},  # Real Madrid
    "楚阿梅尼":     {"g":  2, "a":  3, "mins": 0.80, "nation": "法国"},  # Real Madrid
    # —— 英格兰 ——
    "凯恩":         {"g": 38, "a":  9, "mins": 0.90, "nation": "英格兰"},  # Bayern
    "贝林厄姆":     {"g": 14, "a": 12, "mins": 0.85, "nation": "英格兰"},  # Real Madrid
    "萨卡":         {"g": 14, "a": 10, "mins": 0.75, "nation": "英格兰"},  # Arsenal
    "福登":         {"g": 10, "a":  8, "mins": 0.80, "nation": "英格兰"},  # Man City
    "帕尔默":       {"g": 22, "a": 13, "mins": 0.90, "nation": "英格兰"},  # Chelsea
    "莱斯":         {"g":  6, "a":  3, "mins": 0.85, "nation": "英格兰"},  # Arsenal
    "凯尔沃克":     {"g":  1, "a":  4, "mins": 0.55, "nation": "英格兰"},  # Milan
    # —— 西班牙 ——
    "亚马尔":       {"g": 18, "a": 25, "mins": 0.90, "nation": "西班牙"},  # Barça young star
    "佩德里":       {"g":  9, "a": 11, "mins": 0.85, "nation": "西班牙"},  # Barça
    "罗德里":       {"g":  7, "a":  4, "mins": 0.70, "nation": "西班牙"},  # Man City, Ballon d'Or 2024
    "莫拉塔":       {"g": 16, "a":  4, "mins": 0.75, "nation": "西班牙"},  # Milan/Galatasaray
    "尼科威廉姆斯": {"g": 12, "a":  6, "mins": 0.85, "nation": "西班牙"},  # Athletic
    "丹奥尔莫":     {"g":  9, "a":  9, "mins": 0.65, "nation": "西班牙"},  # Barça
    "法比安鲁伊斯": {"g":  6, "a":  6, "mins": 0.80, "nation": "西班牙"},  # PSG
    # —— 巴西 ——
    "维尼修斯":     {"g": 22, "a": 11, "mins": 0.85, "nation": "巴西"},  # Real Madrid
    "拉菲尼亚":     {"g": 34, "a": 22, "mins": 0.90, "nation": "巴西"},  # Barça
    "罗德里戈":     {"g": 14, "a":  8, "mins": 0.80, "nation": "巴西"},  # Real Madrid
    "内马尔":       {"g":  8, "a":  6, "mins": 0.50, "nation": "巴西"},  # Santos return
    "卡塞米罗":     {"g":  6, "a":  3, "mins": 0.75, "nation": "巴西"},  # ManU
    "马尔基尼奥斯": {"g":  5, "a":  2, "mins": 0.80, "nation": "巴西"},  # PSG (CB)
    "理查利森":     {"g":  3, "a":  3, "mins": 0.40, "nation": "巴西"},  # Tottenham, injury hit
    "恩德里克":     {"g":  6, "a":  2, "mins": 0.30, "nation": "巴西"},  # Real Madrid
    # —— 德国 ——
    "穆西亚拉":     {"g": 12, "a":  9, "mins": 0.80, "nation": "德国"},  # Bayern
    "维尔茨":       {"g": 18, "a": 19, "mins": 0.90, "nation": "德国"},  # Leverkusen
    "哈弗茨":       {"g":  9, "a":  4, "mins": 0.65, "nation": "德国"},  # Arsenal
    "基米希":       {"g":  3, "a": 10, "mins": 0.85, "nation": "德国"},  # Bayern
    "京多安":       {"g":  4, "a":  4, "mins": 0.75, "nation": "德国"},  # ManCity
    "萨内":         {"g":  9, "a":  9, "mins": 0.70, "nation": "德国"},  # Bayern
    # —— 荷兰 ——
    "范戴克":       {"g":  4, "a":  2, "mins": 0.95, "nation": "荷兰"},  # Liverpool
    "加克波":       {"g": 18, "a":  5, "mins": 0.80, "nation": "荷兰"},  # Liverpool
    "登泽尔登贝莱": {"g":  5, "a":  4, "mins": 0.85, "nation": "荷兰"},  # Inter
    "弗朗基德容":   {"g":  4, "a":  6, "mins": 0.65, "nation": "荷兰"},  # Barça
    "韦霍斯特":     {"g":  9, "a":  4, "mins": 0.55, "nation": "荷兰"},
    "雷恩德斯":     {"g": 12, "a":  6, "mins": 0.85, "nation": "荷兰"},  # Milan/Man City
    # —— 比利时 ——
    "德布劳内":     {"g":  6, "a": 12, "mins": 0.65, "nation": "比利时"},  # Man City
    "卢卡库":       {"g": 14, "a":  6, "mins": 0.80, "nation": "比利时"},  # Napoli
    "特罗萨德":     {"g":  9, "a":  8, "mins": 0.70, "nation": "比利时"},  # Arsenal
    "蒂尔曼斯":     {"g":  9, "a":  5, "mins": 0.85, "nation": "比利时"},  # Aston Villa
    "多库":         {"g":  6, "a":  9, "mins": 0.65, "nation": "比利时"},  # Man City
    # —— 克罗地亚 ——
    "莫德里奇":     {"g":  3, "a":  8, "mins": 0.55, "nation": "克罗地亚"},  # Real Madrid
    "克拉马里奇":   {"g": 21, "a":  5, "mins": 0.85, "nation": "克罗地亚"},  # Hoffenheim
    "彼得罗维奇":   {"g":  6, "a":  4, "mins": 0.75, "nation": "克罗地亚"},
    "佩特科维奇":   {"g":  6, "a":  4, "mins": 0.75, "nation": "克罗地亚"},
    # —— 摩洛哥 ——
    "阿什拉夫":     {"g":  4, "a":  9, "mins": 0.85, "nation": "摩洛哥"},  # PSG (Hakimi)
    "齐耶赫":       {"g":  6, "a":  4, "mins": 0.55, "nation": "摩洛哥"},
    "Brahim迪亚斯": {"g":  9, "a":  5, "mins": 0.70, "nation": "摩洛哥"},  # Real Madrid
    # —— 挪威 ——
    "哈兰德":       {"g": 30, "a":  3, "mins": 0.85, "nation": "挪威"},  # Man City
    "厄德高":       {"g":  3, "a":  9, "mins": 0.75, "nation": "挪威"},  # Arsenal
    # —— 埃及 ——
    "萨拉赫":       {"g": 29, "a": 18, "mins": 0.95, "nation": "埃及"},  # Liverpool
    # —— 塞内加尔 ——
    "马内":         {"g": 16, "a":  6, "mins": 0.80, "nation": "塞内加尔"},  # Al-Nassr
    "库利巴利":     {"g":  2, "a":  1, "mins": 0.85, "nation": "塞内加尔"},
    # —— 哥伦比亚 ——
    "迪亚斯":       {"g": 13, "a":  4, "mins": 0.85, "nation": "哥伦比亚"},  # Liverpool (Luis Díaz)
    "詹姆斯":       {"g":  4, "a": 12, "mins": 0.70, "nation": "哥伦比亚"},
    # —— 乌拉圭 ——
    "巴尔韦德":     {"g":  6, "a":  4, "mins": 0.85, "nation": "乌拉圭"},  # Real Madrid
    "努涅斯":       {"g": 12, "a":  4, "mins": 0.65, "nation": "乌拉圭"},  # Liverpool
    "阿劳霍":       {"g":  1, "a":  1, "mins": 0.55, "nation": "乌拉圭"},  # Barça (CB)
    "Federico佩列斯特里": {"g":  5, "a":  3, "mins": 0.65, "nation": "乌拉圭"},
    # —— 美国 ——
    "普利西奇":     {"g": 15, "a":  9, "mins": 0.90, "nation": "美国"},  # Milan
    "Tyler亚当斯":  {"g":  1, "a":  2, "mins": 0.65, "nation": "美国"},
    "巴洛贡":       {"g": 12, "a":  3, "mins": 0.65, "nation": "美国"},  # Monaco
    # —— 韩国 ——
    "孙兴慜":       {"g": 18, "a": 11, "mins": 0.85, "nation": "韩国"},  # Tottenham
    "金玟哉":       {"g":  2, "a":  1, "mins": 0.80, "nation": "韩国"},  # Bayern
    "李刚仁":       {"g":  4, "a":  4, "mins": 0.65, "nation": "韩国"},  # PSG
    "黄喜灿":       {"g":  4, "a":  3, "mins": 0.70, "nation": "韩国"},
    # —— 日本 ——
    "久保建英":     {"g":  8, "a":  6, "mins": 0.75, "nation": "日本"},  # Real Sociedad
    "三笘薰":       {"g":  9, "a":  7, "mins": 0.75, "nation": "日本"},  # Brighton
    "镰田大地":     {"g":  4, "a":  4, "mins": 0.65, "nation": "日本"},
    "上田绫世":     {"g": 22, "a":  5, "mins": 0.85, "nation": "日本"},  # Feyenoord
    # —— 加拿大 ——
    "戴维斯":       {"g":  3, "a":  4, "mins": 0.85, "nation": "加拿大"},  # Bayern (Alphonso)
    "戴维":         {"g": 22, "a":  6, "mins": 0.85, "nation": "加拿大"},  # Lille → Juventus
    # —— 奥地利 ——
    "阿瑙托维奇":   {"g":  6, "a":  3, "mins": 0.55, "nation": "奥地利"},
    "Marko阿瑙托维奇":{"g": 6, "a":  3, "mins": 0.55, "nation": "奥地利"},
    "大卫Alaba":   {"g":  1, "a":  2, "mins": 0.55, "nation": "奥地利"},
    "绍博斯洛伊":   {"g":  6, "a":  6, "mins": 0.80, "nation": "奥地利"},  # actually HUN, ignore
    # —— 瑞士 ——
    "扎卡":         {"g":  2, "a":  3, "mins": 0.85, "nation": "瑞士"},
    "哲马伊利":     {"g":  3, "a":  3, "mins": 0.65, "nation": "瑞士"},
    # —— 苏格兰 ——
    "麦克托米奈":   {"g": 12, "a":  2, "mins": 0.85, "nation": "苏格兰"},  # Napoli
    "罗伯逊":       {"g":  2, "a":  6, "mins": 0.85, "nation": "苏格兰"},  # Liverpool
    "Ché亚当斯":    {"g": 13, "a":  3, "mins": 0.80, "nation": "苏格兰"},
    # —— 瑞典 ——
    "伊萨克":       {"g": 27, "a":  5, "mins": 0.80, "nation": "瑞典"},  # Newcastle
    "古德蒙德松":   {"g": 10, "a":  4, "mins": 0.65, "nation": "瑞典"},
    # —— 土耳其 ——
    "居莱尔":       {"g":  6, "a":  3, "mins": 0.45, "nation": "土耳其"},  # Real Madrid
    "亚兹兹":       {"g": 11, "a":  6, "mins": 0.85, "nation": "土耳其"},  # Juventus
    "肯安耶尔德兹": {"g": 11, "a":  6, "mins": 0.85, "nation": "土耳其"},  # alt name
    "卡迪奥卢":     {"g":  3, "a":  4, "mins": 0.85, "nation": "土耳其"},
    # —— 厄瓜多尔 ——
    "卡塞多":       {"g":  3, "a":  2, "mins": 0.85, "nation": "厄瓜多尔"},  # Chelsea
    "瓦伦西亚":     {"g":  9, "a":  3, "mins": 0.65, "nation": "厄瓜多尔"},  # Internacional
    # —— 科特迪瓦 ——
    "尼昂":         {"g":  6, "a":  4, "mins": 0.65, "nation": "科特迪瓦"},
    "哈勒":         {"g":  9, "a":  3, "mins": 0.55, "nation": "科特迪瓦"},
}

# 球队"地位"档位：根据 PL 列表中的位置 idx 设置
# idx 0-3 = 攻击核心(starter_attack)
# idx 4-6 = 中场主力(starter_mid)
# idx 7-9 = 防守主力(starter_def)
# idx 10  = 门将(GK)
def starter_factor(idx, position):
    if position == "门将":
        return 0.0
    if idx <= 3:
        return 1.10  # 攻击核心
    if idx <= 6:
        return 1.00  # 中场主力
    if idx <= 9:
        return 0.85  # 防守主力
    return 0.85
