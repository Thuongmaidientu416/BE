// Layer 3 - Recommendation Engine
// Tạo danh sách điểm đến gợi ý sau khi đã lọc qua Knowledge Engine

export const generateRecommendations = (userContext, appliedRules) => {
  // Thực tế sẽ fetch từ Database backend và search thuật toán.
  // Đây là mock data trả về danh sách đã được personalize.
  return {
    recommended_route: {
      id: "route_999",
      title: "Date Chill Ngày Mưa Nhẹ",
      total_estimated_cost: "250.000 VNĐ",
      duration: "3h",
      stops: [
        { 
          name: "Đường sách Nguyễn Văn Bình", 
          time: "18:00", 
          note: "Đi dạo dưới hàng cây, có mái che." 
        },
        { 
          name: "Okkio Caffe - Lê Lợi", 
          time: "19:00", 
          note: "Ngắm mưa qua cửa sổ kính, tone màu ấm cúng." 
        }
      ]
    },
    system_rules_used: appliedRules
  };
};
