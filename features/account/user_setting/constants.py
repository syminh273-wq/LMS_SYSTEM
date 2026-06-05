class VoiceNames:
    # Vietnamese
    VI_HOAI_MY = "vi-VN-HoaiMyNeural"
    VI_NAM_MINH = "vi-VN-NamMinhNeural"

    # English (US)
    EN_US_ARIA = "en-US-AriaNeural"
    EN_US_GUY = "en-US-GuyNeural"
    EN_US_JENNY = "en-US-JennyNeural"
    
    # English (UK)
    EN_GB_SONIA = "en-GB-SoniaNeural"
    EN_GB_RYAN = "en-GB-RyanNeural"

    # Chinese
    ZH_CN_XIAOXIAO = "zh-CN-XiaoxiaoNeural"
    ZH_CN_YUNYANG = "zh-CN-YunyangNeural"

    CHOICES = [
        (VI_HOAI_MY, "Vietnamese - Hoai My (Female)"),
        (VI_NAM_MINH, "Vietnamese - Nam Minh (Male)"),
        (EN_US_ARIA, "English (US) - Aria (Female)"),
        (EN_US_GUY, "English (US) - Guy (Male)"),
        (EN_US_JENNY, "English (US) - Jenny (Female)"),
        (EN_GB_SONIA, "English (UK) - Sonia (Female)"),
        (EN_GB_RYAN, "English (UK) - Ryan (Male)"),
        (ZH_CN_XIAOXIAO, "Chinese - Xiaoxiao (Female)"),
        (ZH_CN_YUNYANG, "Chinese - Yunyang (Male)"),
    ]

class UserTypes:
    CONSUMER = "consumer"
    SPACE = "space"
    
    CHOICES = [
        (CONSUMER, "Consumer"),
        (SPACE, "Space"),
    ]
