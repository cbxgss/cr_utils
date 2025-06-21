import unicodedata, string, re


def normalize_text(s):
    s = unicodedata.normalize('NFD', s)

    def lower(text: str):               # 转换为小写            影响很大
        return text.lower()

    def remove_punc(text: str):         # 去除标点符号          影响较小
        CHINESE_PUNCTUATION = "！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～“”‘’、"
        exclude = set(string.punctuation + CHINESE_PUNCTUATION)
        return ''.join([ch for ch in text if ch not in exclude])

    def white_space_fix(text: str):     # 清理多余空格          影响较小
        return ' '.join(text.split()).strip()

    def remove_articles(text: str):     # 去除文章中的冠词      影响较小
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    return white_space_fix(remove_articles(remove_punc(lower(s))))
