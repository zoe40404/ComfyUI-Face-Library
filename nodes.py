# -*- coding: utf-8 -*-
"""Facial Customization —— ComfyUI 角色提示词节点。

两种模式：
  整脸库 —— 性别 → 类型（年龄段/古风）→ 脸型，完整调用该脸的九项字段。
  自由组合 —— 性别 → 类型 →（年龄段时按年龄组过滤）→ 六维独立拼配。

脸型数据由 data 包提供，本模块只做选择映射与提示词拼装。
"""
import json

from .data import load_data

_ENTRY = "沿用该脸默认"
_GROUP_ALL = "不限"
_NONE = "无"
_FTYPE_AGE = "非古风"
_FTYPE_GUFENG = "古风"
_GUFENG = "古风特殊气质组"

_PH_FACE = "（自由组合不用选脸）"
_PH_DIM = "（随脸型自动生成）"
_PH_PROF_NONE = "（无固定职业）"

_GU_GROUPS = ["男童/女童 · ≤12 岁", "少年/少女 · 13–18 岁", "男子/女子 · 19–35 岁", "中年男人/中年女人 · 36–59 岁", "老翁/老妇 · 60–90 岁"]

_GROUP_BOUNDS = {
    "男童/女童 · ≤12 岁": (1, 12),
    "少年/少女 · 13–18 岁": (13, 18),
    "男子/女子 · 19–35 岁": (19, 35),
    "中年男人/中年女人 · 36–59 岁": (36, 59),
    "老翁/老妇 · 60–90 岁": (60, 90),
}

_FIELD_KEY = {"bone": "骨相", "eye": "五官", "hair": "发型", "temper": "气质"}


def _group_short(group):
    """从组名取简短称谓：少女组 → 少女；古风特殊气质组 → 古风。"""
    base = group.split(" · ")[0]
    if base == "古风特殊气质组":
        return "古风"
    return base.replace("组", "")


def _group_range(group):
    """从组名取年龄段：少女组 · 16–22 岁 → 16–22岁。"""
    if " · " in group:
        return group.split(" · ")[1].replace(" ", "")
    return None


def _gender_term(is_male, age=None):
    """性别类别：男童/女童、少年/少女、男子/女子、中年男人/中年女人、老翁/老妇。"""
    if age is None:
        return "男子" if is_male else "女子"
    if age <= 12:
        return "男童" if is_male else "女童"
    if age <= 18:
        return "少年" if is_male else "少女"
    if age <= 35:
        return "男子" if is_male else "女子"
    if age <= 59:
        return "中年男人" if is_male else "中年女人"
    return "老翁" if is_male else "老妇"


def _gufeng_role(is_male, role):
    """古风整脸库 [年龄] 的职业+性别：女→女刺客，男→男刺客。"""
    prof = role or ""
    if not is_male and prof.startswith("女"):
        prof = prof[1:]
    return ("女" if not is_male else "男") + prof


def _group_bounds(group):
    """年龄组的 (min, max) 边界；未知组返回 (None, None)。"""
    return _GROUP_BOUNDS.get(group, (None, None))


def _group_mid_age(group):
    """取年龄组区间的中间年龄。"""
    lo, hi = _group_bounds(group)
    if lo is not None and hi is not None:
        return (lo + hi) // 2
    return None


def _menu_line(menu, label):
    """菜单项转正文；若正文未含标签，则前置「标签，」。"""
    for it in menu:
        if it["label"] == label:
            text = it["text"]
            stripped = text.replace(" ", "")
            tokens = [t.strip() for t in label.split("·")]
            if all(t.replace(" ", "") in stripped for t in tokens):
                return text
            return label + "，" + text
    return label


_KW_MAP = None


def _get_kw_map(data):
    """构建「简洁标签 → 完整字段」映射（按性别分；makeup 分妆容/面部）。"""
    global _KW_MAP
    if _KW_MAP is None:
        _KW_MAP = {}
        for gender_key, entries_list in (("F", data["female"]), ("M", data["male"])):
            gmap = {}
            for dim in ("makeup", "bone", "eye", "hair", "temper"):
                m = {}
                for e in entries_list:
                    kw_val = e["kw"][dim]
                    if kw_val and kw_val not in m:
                        if dim == "makeup":
                            full = e["fields"].get("妆容") or e["fields"].get("面部")
                        else:
                            full = e["fields"][_FIELD_KEY[dim]]
                        m[kw_val] = full
                gmap[dim] = m
            _KW_MAP[gender_key] = gmap
    return _KW_MAP


def _parse_age(s):
    """把 age_input（字符串/数字/占位符）解析为具体年龄；非数字或 ≤0 返回 0（表示自动）。"""
    try:
        v = int(str(s).strip())
        return v if v > 0 else 0
    except (ValueError, TypeError):
        return 0


class FacialCustomization:
    CATEGORY = "Character Customization"
    FUNCTION = "generate"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "negative", "meta")
    OUTPUT_NODE = False
    DESCRIPTION = "中式人物资产提示词生成：选脸/拼配 + 画风/光/镜头/姿态"

    @classmethod
    def INPUT_TYPES(cls):
        d = load_data()
        menus = d["menus"]
        female = d["female"]
        male = d["male"]

        def dedup(vals):
            seen = set()
            out = []
            for v in vals:
                if v and v not in seen:
                    seen.add(v)
                    out.append(v)
            return out

        def titles(es):
            return [e["title"] for e in es]

        def dims_full(es, dim):
            vals = []
            for e in es:
                if dim == "anchor":
                    vals.extend(e["anchors"])
                else:
                    vals.append(e["kw"][dim])
            return dedup(vals)

        def groups(es):
            seen = []
            for e in es:
                if e["group"] not in seen:
                    seen.append(e["group"])
            return seen

        def gufeng_profs():
            out = []
            for e in female + male:
                if e["group"] == _GUFENG and e["role"] and e["role"] not in out:
                    out.append(e["role"])
            return out

        f_age = [e for e in female if e["group"] != _GUFENG]
        m_age = [e for e in male if e["group"] != _GUFENG]

        style_opts = [it["label"] for it in menus["style"]]
        light_opts = [it["label"] for it in menus["light"]]
        camera_opts = [_ENTRY] + [it["label"] for it in menus["camera"]]
        pose_opts = [_ENTRY] + [it["label"] for it in menus["pose"]]
        prof_opts = [_PH_DIM, _PH_PROF_NONE] + gufeng_profs()

        return {
            "required": {
                "mode": (["整脸库", "自由组合"], {"default": "整脸库"}),
                "gender": (["女性", "男性"], {"default": "女性"}),
                "ftype": ([_FTYPE_AGE, _FTYPE_GUFENG], {"default": _FTYPE_AGE}),
                "age_group": ([_GROUP_ALL] + _GU_GROUPS, {"default": _GROUP_ALL}),
                "age_input": ("STRING", {"default": "18", "multiline": False}),
                "profession": (prof_opts, {"default": _PH_DIM}),
                "face": (titles(female) + titles(male) + [_PH_FACE], {"default": titles(f_age)[0]}),
                "makeup": (dims_full(female, "makeup") + dims_full(male, "makeup") + [_PH_DIM], {"default": dims_full(female, "makeup")[0]}),
                "bone": (dims_full(female, "bone") + dims_full(male, "bone") + [_PH_DIM], {"default": dims_full(female, "bone")[0]}),
                "eye": (dims_full(female, "eye") + dims_full(male, "eye") + [_PH_DIM], {"default": dims_full(female, "eye")[0]}),
                "hair": (dims_full(female, "hair") + dims_full(male, "hair") + [_PH_DIM], {"default": dims_full(female, "hair")[0]}),
                "anchor": ([_NONE] + dims_full(female, "anchor") + dims_full(male, "anchor") + [_PH_DIM], {"default": _NONE}),
                "temper": (dims_full(female, "temper") + dims_full(male, "temper") + [_PH_DIM], {"default": dims_full(female, "temper")[0]}),
                "style": (style_opts, {"default": style_opts[0]}),
                "light": (light_opts, {"default": "均匀柔光（近平光）" if "均匀柔光（近平光）" in light_opts else light_opts[0]}),
                "camera": (camera_opts, {"default": _ENTRY}),
                "pose": (pose_opts, {"default": _ENTRY}),
            }
        }

    def generate(self, mode, gender, ftype, age_group, age_input, profession, face, makeup, bone, eye, hair,
                 anchor, temper, style, light, camera, pose):
        d = load_data()
        entries = d["entries"]
        menus = d["menus"]

        if mode == "整脸库":
            eid = face.split(" · ")[0].strip()
            e = entries[eid]
            is_male = eid.startswith("M")
            gender_line = e["fields"].get("性别", "")
            makeup_line = e["fields"].get("面部" if is_male else "妆容", "")
            bone_line = e["fields"].get("骨相", "")
            eye_line = e["fields"].get("五官", "")
            hair_line = e["fields"].get("发型", "")
            anchor_line = e["fields"].get("识别", "")
            temper_line = e["fields"].get("气质", "")
            camera_default = e["fields"].get("镜头", "")
            pose_default = e["fields"].get("姿态", "")
            age_num = int(e["age"].replace(" 岁", "")) if e["age"] else None
            if e["group"] == _GUFENG:
                age_text = str(age_num) + "岁古装" + _gufeng_role(is_male, e.get("role"))
            else:
                age_text = str(age_num) + "岁" + _gender_term(is_male, age_num)
            profession_line = None
            selection = {"face": eid}
        else:  # 自由组合
            is_male = (gender == "男性")
            gender_line = "一位男性，东方男性面孔" if is_male else "一位女性，东方女性面孔"
            kw_map = _get_kw_map(d)["M" if is_male else "F"]
            makeup_line = kw_map["makeup"].get(makeup, makeup)
            bone_line = kw_map["bone"].get(bone, bone)
            eye_line = kw_map["eye"].get(eye, eye)
            hair_line = kw_map["hair"].get(hair, hair)
            anchor_line = None if anchor == _NONE else anchor
            temper_line = kw_map["temper"].get(temper, temper)
            camera_default = menus["camera"][0]["text"]
            pose_default = menus["pose"][0]["text"]
            age_val = _parse_age(age_input)
            if age_val > 0:
                if ftype == _FTYPE_GUFENG:
                    age_text = str(age_val) + "岁古装" + _gender_term(is_male, age_val)
                else:
                    age_text = str(age_val) + "岁" + _gender_term(is_male, age_val)
            elif age_group and age_group != _GROUP_ALL:
                rng = _group_range(age_group) or ""
                mid = _group_mid_age(age_group)
                if ftype == _FTYPE_GUFENG:
                    age_text = rng + "古装" + _gender_term(is_male, mid)
                else:
                    age_text = rng + _gender_term(is_male, mid)
            else:
                age_text = None
            profession_line = None
            if ftype == _FTYPE_GUFENG and profession and profession not in (_PH_PROF_NONE, _PH_DIM):
                profession_line = profession
            selection = {
                "makeup": makeup, "bone": bone, "eye": eye,
                "hair": hair, "anchor": anchor, "temper": temper,
            }

        camera_line = camera_default if camera == _ENTRY else _menu_line(menus["camera"], camera)
        pose_line = pose_default if pose == _ENTRY else _menu_line(menus["pose"], pose)
        style_text = _menu_line(menus["style"], style)
        light_text = _menu_line(menus["light"], light)

        makeup_tag = "面部" if is_male else "妆容"

        lines = ["[性别] " + gender_line]
        if age_text:
            lines.append("[年龄] " + age_text)
        if profession_line:
            lines.append("[职业] " + profession_line)
        lines.append("[" + makeup_tag + "] " + makeup_line)
        lines.append("[骨相] " + bone_line)
        lines.append("[五官] " + eye_line)
        lines.append("[发型] " + hair_line)
        if anchor_line:
            lines.append("[识别] " + anchor_line)
        lines.append("[气质] " + temper_line)
        lines.append("[镜头] " + camera_line)
        lines.append("[姿态] " + pose_line)
        lines.append("[画风] " + style_text)
        lines.append("[光] " + light_text)

        prompt = "\n".join(lines)

        neg = list(d["negative_words"])
        neg.append("女性化" if is_male else "男性化")
        negative = ", ".join(neg)

        meta = {
            "mode": mode,
            "gender": gender,
            "ftype": ftype,
            "age_group": age_group,
            "age": age_text,
            "style": style,
            "light": light,
            "camera": camera,
            "pose": pose,
            "selection": selection,
        }
        meta_str = json.dumps(meta, ensure_ascii=False, indent=1)

        return (prompt, negative, meta_str)
