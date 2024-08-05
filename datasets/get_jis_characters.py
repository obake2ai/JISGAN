def generate_jis_characters():
    # JIS各規格に対応するUnicode範囲を定義
    jis_ranges = [
        # JIS X 0201: ASCIIと半角カタカナ
        (0x0020, 0x007E),  # ASCII (JIS X 0201)
        (0x00A1, 0x00DF),  # 半角カタカナ (JIS X 0201)

        # JIS X 0208: ひらがな、カタカナ、CJK統合漢字など
        (0x3000, 0x303F),  # CJK記号および句読点 (JIS X 0208)
        (0x3040, 0x309F),  # ひらがな (JIS X 0208)
        (0x30A0, 0x30FF),  # カタカナ (JIS X 0208)
        (0x4E00, 0x9FFF),  # CJK統合漢字 (JIS X 0208, 0213)

        # JIS X 0212: 補助漢字
        (0x3400, 0x4DBF),  # CJK統合漢字拡張A (JIS X 0212, 0213)
        (0xF900, 0xFAFF),  # CJK互換漢字 (JIS X 0212)

        # JIS X 0213: 拡張漢字セット
        (0x20000, 0x2A6DF), # CJK統合漢字拡張B (JIS X 0213)
        (0x2A700, 0x2B73F), # CJK統合漢字拡張C (JIS X 0213)
        (0x2B740, 0x2B81F), # CJK統合漢字拡張D (JIS X 0213)
        (0x2B820, 0x2CEAF), # CJK統合漢字拡張E (JIS X 0213)
        (0x2CEB0, 0x2EBEF)  # CJK統合漢字拡張F (JIS X 0213)
    ]

    jis_characters = []

    for start, end in jis_ranges:
        for code_point in range(start, end + 1):
            jis_characters.append(chr(code_point))

    return jis_characters

if __name__ == '__main__':
    jis_characters = generate_jis_characters()
    print(' '.join(jis_characters[:100]))
    print("total num: ", len(jis_characters))
