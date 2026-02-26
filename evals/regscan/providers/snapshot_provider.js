/**
 * Snapshot Provider — 기존 브리핑 JSON을 promptfoo assertion에 그대로 제공
 *
 * 스냅샷 디렉터리에서 INN 기반으로 기사 파일을 로드하고,
 * 레거시 필드명(global_section 등)을 V4 필드명(global_insight_text 등)으로 매핑하여
 * JSON 문자열로 반환한다. LLM 호출 없음.
 */
const fs = require("fs");
const path = require("path");

// 레거시 → V4 필드명 매핑
const FIELD_MAP = {
  global_section: "global_insight_text",
  domestic_section: "domestic_insight_text",
  medclaim_section: "medclaim_action_text",
};

class SnapshotProvider {
  constructor(options) {
    this.dir = options.config.snapshotDir;
    this.label = options.config.label || path.basename(this.dir);
  }

  id() {
    return `snapshot:${this.label}`;
  }

  /**
   * @param {string} prompt - promptfoo가 전달하는 프롬프트 (여기서는 무시하고 vars에서 INN 추출)
   * @param {object} context - { vars }
   */
  async callApi(prompt, context) {
    // vars.drug_data JSON에서 INN 추출
    let inn;
    try {
      const drugData = JSON.parse(context.vars.drug_data);
      inn = drugData.inn;
    } catch (e) {
      return { error: "drug_data JSON parse failed: " + e.message };
    }

    if (!inn) {
      return { error: "INN not found in drug_data" };
    }

    // INN → 파일명 변환 시도 (대소문자 변형)
    const candidates = [
      `${inn.toUpperCase()}.json`,
      `${inn}.json`,
      `${inn.toLowerCase()}.json`,
      // 공백/하이픈 → 언더스코어
      `${inn.toUpperCase().replace(/[\s-]+/g, "_")}.json`,
      `${inn.replace(/[\s-]+/g, "_")}.json`,
    ];

    let filePath = null;
    for (const candidate of candidates) {
      const p = path.join(this.dir, candidate);
      if (fs.existsSync(p)) {
        filePath = p;
        break;
      }
    }

    if (!filePath) {
      // 디렉터리 내 case-insensitive 검색
      try {
        const files = fs.readdirSync(this.dir);
        const innUpper = inn.toUpperCase().replace(/[\s-]+/g, "_");
        const match = files.find(
          (f) =>
            f.endsWith(".json") &&
            !f.startsWith("_") &&
            f.replace(".json", "").toUpperCase().replace(/[\s-]+/g, "_") === innUpper
        );
        if (match) filePath = path.join(this.dir, match);
      } catch (e) {
        return { error: "Directory read failed: " + e.message };
      }
    }

    if (!filePath) {
      return { error: `Briefing not found for INN "${inn}" in ${this.dir}` };
    }

    // 브리핑 JSON 로드
    let briefing;
    try {
      briefing = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    } catch (e) {
      return { error: "Briefing JSON parse failed: " + e.message };
    }

    // V4 6필드 JSON 구성 (레거시 필드명 → V4 매핑)
    const output = {
      headline: briefing.headline || "",
      subtitle: briefing.subtitle || "",
      key_points: briefing.key_points || [],
      global_insight_text:
        briefing.global_insight_text || briefing.global_section || "",
      domestic_insight_text:
        briefing.domestic_insight_text || briefing.domestic_section || "",
      medclaim_action_text:
        briefing.medclaim_action_text || briefing.medclaim_section || "",
    };

    return {
      output: JSON.stringify(output, null, 2),
      tokenUsage: { total: 0, prompt: 0, completion: 0 },
    };
  }
}

module.exports = SnapshotProvider;
