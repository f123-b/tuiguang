"""Creative intent is an instruction, never proof of artistic quality."""

VERSION = "story_direction@1"
ARCS = {
    "overview": ["hook", "evidence", "payoff"],
    "story": ["hook", "friction", "turn", "evidence", "payoff"],
    "contrast": ["hook", "friction", "turn", "evidence", "payoff"],
    "documentary": ["hook", "context", "evidence", "reflection", "payoff"],
}


def direction(document):
    mode = document.get("narrative_mode", "overview")
    return {
        "version": VERSION,
        "mode": mode,
        "arc": ARCS[mode],
        "require_concrete_example": mode != "overview",
        "fiction_must_be_labeled": True,
        "allow_unverified_product_claims": False,
        "quality_status": "requires_human_judgment",
        "editing": [
            "先给观众一个具体的人物处境或问题，不以品牌口号和功能清单开场",
            "每镜推进一个信息，采用有目的的长短节奏；不强制均分时长",
            "至少一个具体例子解释为什么、怎么做或如何验证；示例不能冒充客户事实",
            "让已核实的产品操作成为解决问题的证据，不把软件描述为保证结果的魔法",
            "画面承担动作与证据，旁白补充因果和情绪；不要逐字朗读所有字幕",
            "转折可用反问、停顿或轻微反差；不捏造访谈、评价、AI回答或人物背书",
            "结尾回扣开场问题，给一个具体可执行的小行动",
            "只选择已有授权素材，缺少的角色表演、实拍或音色列入uncertainties，画面建议不是已生成画面",
        ],
    }
