// Layer 2 - Travel Knowledge Engine
// Áp dụng các quy tắc (rules), lọc dữ liệu dựa trên thời tiết, ngân sách, traffic...

export const applyTravelRules = (userContext) => {
  let rulesApplied = [];
  
  if (userContext.context.weather.includes("Mưa")) {
    rulesApplied.push("Tránh hoạt động ngoài trời, ưu tiên địa điểm trong nhà hoặc có mái che.");
  }
  
  if (userContext.user.budget < 500000) {
    rulesApplied.push("Ưu tiên địa điểm miễn phí hoặc quán cafe/street food giá hợp lý.");
  }
  
  if (userContext.context.traffic === "Kẹt xe") {
    rulesApplied.push("Ưu tiên các địa điểm gần nhau, có thể đi bộ để tránh kẹt xe.");
  }

  return rulesApplied;
};
