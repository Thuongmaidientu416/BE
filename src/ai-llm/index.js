import { getUserContext } from './Layer1_DataEngine';
import { applyTravelRules } from './Layer2_KnowledgeEngine';
import { generateRecommendations } from './Layer3_RecommendationEngine';
import { generateAIResponse } from './Layer4_ConversationLayer';

/**
 * Hàm Orchestrator kết nối 4 Layer của AI LLM Architecture.
 * Backend sau này sẽ gọi hàm tương tự để điều phối luồng dữ liệu.
 */
export const processUserMessage = async (userMessage, messageHistory, groqKey) => {
  // 1. Lấy Context người dùng
  const context = getUserContext("user_w123", userMessage);
  
  // 2. Chạy qua Knowledge Engine để lấy các Rule nghiệp vụ
  const rules = applyTravelRules(context);
  
  // 3. Chạy qua Recommendation Engine để sinh lộ trình
  const recommendations = generateRecommendations(context, rules);
  
  // Đóng gói data lại gửi cho LLM
  const systemData = {
    userProfile: context.user,
    liveContext: context.context,
    businessRulesApplied: rules,
    recommendations: recommendations
  };

  // 4. Gọi LLM để biên dịch thành câu thoại tự nhiên
  const aiReply = await generateAIResponse(userMessage, messageHistory, groqKey, systemData);
  
  return aiReply;
};
