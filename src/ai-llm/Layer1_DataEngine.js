// Layer 1 - Data & Tracking Engine
// Lấy dữ liệu hồ sơ người dùng, lịch trình, ngữ cảnh thời gian thực (Giả lập BE)

export const getUserContext = (userId, intentMsg) => {
  // Mock data mô phỏng dữ liệu trả về từ Database
  return {
    user: {
      id: userId,
      name: "Khách",
      preferences: ["rooftop", "cafe", "chụp ảnh", "cảnh đêm", "food"],
      budget: 350000,
    },
    context: {
      location: "Quận 1, TP.HCM",
      weather: "Mưa nhẹ",
      traffic: "Bình thường",
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    },
    intent: intentMsg
  };
};
