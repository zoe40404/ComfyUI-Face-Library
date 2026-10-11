import { app } from "../../scripts/app.js";
import { FACE_DB } from "./face_data.js";

const NODE_NAME = "FacialCustomization";
const ALL = "不限";
const NONE = "无";
const ENTRY = "沿用该脸默认";
const FTYPE_AGE = "非古风";
const FTYPE_GUFENG = "古风";
const DIMS = ["makeup", "bone", "eye", "hair", "anchor", "temper"];

const PH_FACE = "（自由组合不用选脸）";
const PH_DIM = "（随脸型自动生成）";
const PH_PROF_NONE = "（无固定职业）";

function getWidget(node, name) {
    return node.widgets ? node.widgets.find((w) => w.name === name) : null;
}

function groupBounds(groupName) {
    if (!groupName) return null;
    if (String(groupName).includes("≤12")) return [1, 12];
    const m = String(groupName).match(/(\d+)[–-](\d+)/);
    if (m) return [parseInt(m[1], 10), parseInt(m[2], 10)];
    return null;
}

function dedup(arr) {
    const seen = new Set();
    const out = [];
    for (const x of arr) {
        if (x && !seen.has(x)) {
            seen.add(x);
            out.push(x);
        }
    }
    return out;
}

function refresh(node) {
    const modeW = getWidget(node, "mode");
    const genderW = getWidget(node, "gender");
    const ftypeW = getWidget(node, "ftype");
    const groupW = getWidget(node, "age_group");
    const faceW = getWidget(node, "face");

    const mode = modeW ? modeW.value : "整脸库";
    const gender = genderW ? genderW.value : "女性";
    const ftype = ftypeW ? ftypeW.value : FTYPE_AGE;
    const gdb = FACE_DB[gender];
    if (!gdb) return;

    // 1) 年龄组：古风类型用古风年龄组，非古风用年龄段组
    if (groupW) {
        if (ftype === FTYPE_GUFENG) {
            groupW.options.values = [ALL].concat(gdb.gufeng.groups);
            if (!groupW.options.values.includes(groupW.value)) {
                groupW.value = ALL;
            }
        } else {
            groupW.options.values = [ALL].concat(gdb.age.groups);
            if (!groupW.options.values.includes(groupW.value)) {
                groupW.value = ALL;
            }
        }
    }
    const group = groupW ? groupW.value : ALL;

    // 1.5) 年龄输入：整脸库锁定占位；自由组合按年龄组钳制/自动代入
    const ageInputW = getWidget(node, "age_input");
    if (ageInputW) {
        if (mode === "整脸库") {
            ageInputW.value = PH_DIM;
        } else {
            const bounds = group !== ALL ? groupBounds(group) : null;
            const cur = String(ageInputW.value || "").trim();
            const isNum = /^\d+$/.test(cur);
            if (bounds) {
                if (!isNum) {
                    ageInputW.value = String(bounds[0]);
                } else if (node._prevGroup !== group) {
                    // 切换年龄组 → 自动代入最小年龄
                    ageInputW.value = String(bounds[0]);
                } else {
                    let v = parseInt(cur, 10);
                    if (v < bounds[0]) v = bounds[0];
                    if (v > bounds[1]) v = bounds[1];
                    ageInputW.value = String(v);
                }
            } else if (!isNum) {
                ageInputW.value = "18";
            }
        }
    }
    node._prevGroup = group;

    // 1.6) 职业：整脸库/非古风锁定占位；自由组合古风列职业
    const profW = getWidget(node, "profession");
    if (profW) {
        if (mode === "整脸库") {
            profW.options.values = [PH_DIM];
            profW.value = PH_DIM;
        } else if (ftype === FTYPE_GUFENG) {
            const plist = [PH_PROF_NONE].concat(gdb.gufeng.professions || []);
            profW.options.values = plist;
            if (!plist.includes(profW.value)) {
                profW.value = PH_PROF_NONE;
            }
        } else {
            profW.options.values = [PH_PROF_NONE];
            profW.value = PH_PROF_NONE;
        }
    }

    // 2) 脸型：自由组合锁定占位；整脸库按类型列脸
    if (faceW) {
        if (mode === "自由组合") {
            faceW.options.values = [PH_FACE];
            faceW.value = PH_FACE;
        } else if (ftype === FTYPE_GUFENG) {
            const faces = group === ALL
                ? gdb.gufeng.groups.reduce((acc, g) => acc.concat(gdb.gufeng.faces[g] || []), [])
                : (gdb.gufeng.faces[group] || []);
            faceW.options.values = faces;
            if (!faces.includes(faceW.value)) {
                faceW.value = faces[0] || "";
            }
        } else {
            const faces = group === ALL
                ? gdb.age.groups.reduce((acc, g) => acc.concat(gdb.age.faces[g] || []), [])
                : (gdb.age.faces[group] || []);
            faceW.options.values = faces;
            if (!faces.includes(faceW.value)) {
                faceW.value = faces[0] || "";
            }
        }
    }

    // 3) 六维：整脸库锁定占位；自由组合按类型列去重池
    for (const dim of DIMS) {
        const w = getWidget(node, dim);
        if (!w) continue;
        if (mode === "整脸库") {
            w.options.values = [PH_DIM];
            w.value = PH_DIM;
        } else if (ftype === FTYPE_GUFENG) {
            let list = group === ALL
                ? dedup(gdb.gufeng.groups.reduce((acc, g) => acc.concat(gdb.gufeng.dims[dim][g] || []), []))
                : (gdb.gufeng.dims[dim][group] || []);
            if (dim === "anchor") {
                list = [NONE].concat(list);
            }
            w.options.values = list;
            if (!list.includes(w.value)) {
                w.value = list[0] || "";
            }
        } else {
            let list = group === ALL
                ? dedup(gdb.age.groups.reduce((acc, g) => acc.concat(gdb.age.dims[dim][g] || []), []))
                : (gdb.age.dims[dim][group] || []);
            if (dim === "anchor") {
                list = [NONE].concat(list);
            }
            w.options.values = list;
            if (!list.includes(w.value)) {
                w.value = list[0] || "";
            }
        }
    }

    // 4) 镜头/姿态：整脸库含「沿用该脸默认」，自由组合仅菜单项
    const menus = FACE_DB.menus || {};
    const cameraW = getWidget(node, "camera");
    const poseW = getWidget(node, "pose");
    if (cameraW && menus.camera) {
        const list = mode === "整脸库" ? [ENTRY].concat(menus.camera) : menus.camera.slice();
        cameraW.options.values = list;
        if (!list.includes(cameraW.value)) {
            cameraW.value = list[0] || "";
        }
    }
    if (poseW && menus.pose) {
        const list = mode === "整脸库" ? [ENTRY].concat(menus.pose) : menus.pose.slice();
        poseW.options.values = list;
        if (!list.includes(poseW.value)) {
            poseW.value = list[0] || "";
        }
    }

    // 5) 画风/光：旧工作流错位值自动复位
    const styleW = getWidget(node, "style");
    const lightW = getWidget(node, "light");
    if (styleW && menus.style) {
        if (!menus.style.includes(styleW.value)) {
            styleW.value = menus.style[0];
        }
    }
    if (lightW && menus.light) {
        if (!menus.light.includes(lightW.value)) {
            lightW.value = menus.light[0];
        }
    }
}

function setupCascade(node) {
    const hook = (name) => {
        const w = getWidget(node, name);
        if (!w) return;
        const orig = w.callback;
        w.callback = function () {
            refresh(node);
            if (orig) orig.apply(this, arguments);
        };
    };
    hook("mode");
    hook("gender");
    hook("ftype");
    hook("age_group");

    // 年龄输入：自由组合下手动输入时按年龄组钳制
    const ageInputW = getWidget(node, "age_input");
    if (ageInputW) {
        const origAge = ageInputW.callback;
        ageInputW.callback = function () {
            const g = getWidget(node, "age_group");
            const group = g ? g.value : ALL;
            if (group !== ALL) {
                const bounds = groupBounds(group);
                if (bounds) {
                    const cur = String(ageInputW.value || "").trim();
                    if (/^\d+$/.test(cur)) {
                        let v = parseInt(cur, 10);
                        if (v < bounds[0]) v = bounds[0];
                        if (v > bounds[1]) v = bounds[1];
                        ageInputW.value = String(v);
                    }
                }
            }
            if (origAge) origAge.apply(this, arguments);
        };
    }

    setTimeout(() => refresh(node), 0);
}

app.registerExtension({
    name: "ComfyUI.FaceLibrary.Cascade",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
            setupCascade(this);
            return r;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const r = onConfigure ? onConfigure.apply(this, arguments) : undefined;
            setTimeout(() => refresh(this), 0);
            return r;
        };
    },
});
