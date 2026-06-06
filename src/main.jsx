import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import * as THREE from "three";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  Camera,
  CalendarDays,
  Car,
  Check,
  ChevronRight,
  Clock3,
  Compass,
  Coffee,
  CreditCard,
  Facebook,
  Gem,
  Globe2,
  Headphones,
  Instagram,
  LockKeyhole,
  Mail,
  MapPin,
  Menu,
  MessageCircle,
  Navigation,
  Phone,
  Plane,
  RefreshCcw,
  Route as RouteIcon,
  ShieldCheck,
  Sparkles,
  Star,
  Settings,
  Utensils,
  Wallet,
  X,
} from "lucide-react";
import "./styles.css";
import { processUserMessage } from "./ai-llm/index";
import { apiLogin, apiRegister, apiGenerateItinerary, apiRerouteItinerary, apiSubmitContact, apiTrackInteraction, apiSelectPlan, apiGetMyPlan, apiGetMe, clearToken, setToken } from "./api";

const navItems = [
  ["Trang chủ", "/"],
  ["Về WanderHUB", "/about"],
  ["Gói dịch vụ", "/pricing"],
  ["Khám phá", "/explore"],
  ["Liên hệ", "/contact"],
];

const packages = [
  {
    name: "Basic",
    price: "Miễn phí",
    note: "Dành cho người mới trải nghiệm WanderHUB — giới hạn 2 lịch trình AI mỗi tháng.",
    features: [
      "Tạo lịch trình AI (2 lần/tháng)",
      "Khám phá địa điểm cơ bản",
      "Gợi ý theo mood & khu vực",
      "Bản đồ hành trình",
    ],
    notIncluded: [
      "Hidden Gems & địa điểm độc quyền",
      "Re-route thông minh realtime",
      "Ưu tiên tài xế giờ cao điểm",
      "Hỗ trợ chat 24/7",
    ],
  },
  {
    name: "Premium",
    price: "89.000 VNĐ/tháng",
    note: "Gói tốt nhất cho người đi chơi thường xuyên tại TP.HCM.",
    highlight: true,
    features: [
      "Không giới hạn lịch trình AI",
      "Ưu tiên tài xế giờ cao điểm",
      "Mở khóa 100% Hidden Gems",
      "Re-route thông minh realtime",
      "Hỗ trợ chat 24/7",
      "Tích hợp Xanh SM & Be",
    ],
    notIncluded: ["Trợ lý đa ngôn ngữ"],
  },
  {
    name: "International Tourist",
    price: "Từ 199.000 VNĐ/hành trình",
    note: "Trợ lý đô thị cho du khách quốc tế khám phá TP.HCM.",
    features: [
      "Trợ lý ảo đa ngôn ngữ (EN/JP/KR)",
      "Hỗ trợ sự cố 24/7",
      "Local assistant option",
      "Không giới hạn lịch trình",
      "Đặt xe & thanh toán quốc tế",
      "Bản đồ offline có sẵn",
    ],
    notIncluded: [],
  },
];

const faqItems = [
  {
    q: "AI của WanderHUB hoạt động như thế nào?",
    a: "WanderHUB phân tích mood, thời gian rảnh, ngân sách, quận yêu thích, khẩu vị và cách di chuyển để dựng tuyến đi chơi phù hợp theo từng bối cảnh đô thị. Mô hình AI liên tục học từ hành vi và phản hồi thực tế của người dùng.",
  },
  {
    q: "Tôi có bị tính thêm phụ phí khi đặt xe công nghệ không?",
    a: "Không có phụ phí ẩn từ WanderHUB cho phần xe. Chi phí di chuyển được hiển thị theo giá thị trường hoặc theo điều kiện của đối tác vận chuyển tại thời điểm đặt. WanderHUB chỉ kết nối bạn với dịch vụ phù hợp.",
  },
  {
    q: "Đang đi chơi mà muốn thay đổi điểm đến giữa chừng thì sao?",
    a: "Bạn có thể dùng tính năng Re-route để AI đề xuất điểm thay thế gần nhất, cân lại thời gian, chi phí và phương án di chuyển mới. Tính năng này hoạt động realtime và có sẵn cho tài khoản Premium.",
  },
  {
    q: "WanderHUB chấp nhận thanh toán nào?",
    a: "WanderHUB hỗ trợ thẻ nội địa (Visa/Mastercard/JCB), ví điện tử (MoMo, ZaloPay, VNPay), chuyển khoản ngân hàng và thanh toán tiền mặt qua đối tác. Giao dịch được mã hóa bảo mật theo chuẩn PCI DSS.",
  },
  {
    q: "Dữ liệu vị trí của tôi có được bảo vệ không?",
    a: "Dữ liệu vị trí chỉ được sử dụng trong phiên khám phá và không được lưu trữ lâu dài nếu bạn không đồng ý. WanderHUB tuân thủ Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân tại Việt Nam.",
  },
  {
    q: "Tôi có thể hủy Premium bất kỳ lúc nào không?",
    a: "Có. Bạn có thể hủy đăng ký Premium bất kỳ lúc nào từ trang tài khoản. Gói sẽ còn hiệu lực đến hết kỳ thanh toán hiện tại và không có phí hủy.",
  },
];

// --- MOCK DATABASE TẠM THỜI (Chuẩn bị thay bằng API/Database thật) ---
const mockExploreDB = [
  {
    id: "loc-001",
    title: "Secret Garden Rooftop",
    summary: "Rooftop ẩn giữa Q1 với view phố cổ, món Việt gia truyền và không khí riêng tư.",
    image: "/images/secret-garden.png",
    readTime: "4 phút đọc",
    author: "Minh Thư (Travel Blogger)",
    content: "Nằm ẩn mình trên tầng thượng của một khu chung cư cũ trên đường Pasteur, Secret Garden đưa du khách vào một không gian đậm chất làng quê Việt Nam thanh bình. Với giàn dây leo xanh mát, những bộ bàn ghế gỗ mộc mạc và ánh đèn vàng ấm áp, đây là địa điểm lý tưởng để thưởng thức các món ăn gia đình truyền thống sau một ngày làm việc căng thẳng.\n\nKhông khí tại quán vô cùng trong lành và tách biệt hoàn toàn khỏi nhịp xe cộ hối hả của Quận 1 bên dưới. Bạn có thể gọi một đĩa thịt kho quẹt đậm đà, vài món rau luộc giản dị và một ly nước thảo mộc mát lành để khép lại một ngày thật nhẹ nhõm."
  },
  {
    id: "loc-002",
    title: "Phố đi bộ Nguyễn Huệ",
    summary: "Trục kết nối trung tâm – cafe, check-in và dạo phố đêm hợp mood Gen Z.",
    image: "/images/nguyen-hue.jpg",
    readTime: "3 phút đọc",
    author: "Hoàng Nam (Urban Photographer)",
    content: "Phố đi bộ Nguyễn Huệ luôn là tâm điểm giải trí của người dân và du khách tại TP.HCM. Từ các buổi biểu diễn âm nhạc đường phố đầy ngẫu hứng đến những quán cà phê chung cư 42 Nguyễn Huệ có ban công ngắm phố từ trên cao, nơi đây mang đậm hơi thở năng động và cởi mở của Sài Gòn.\n\nVào ban đêm, toàn bộ khu phố bừng sáng dưới ánh đèn neon rực rỡ. Đây là nơi bạn có thể thưởng thức trà dâu, ăn bánh tráng trộn và ngắm dòng người qua lại hoặc đón một chiếc xe điện Xanh SM để bắt đầu hành trình vi vu đêm của mình."
  },
  {
    id: "loc-003",
    title: "Ốc Đào – Seafood local",
    summary: "Quán ốc huyền thoại Sài Gòn, trải nghiệm ăn uống đường phố đúng chất.",
    image: "/images/oc-dao.png",
    readTime: "5 phút đọc",
    author: "Kiệt Anh (Food Reviewer)",
    content: "Đối với người Sài Gòn, đi ăn ốc không chỉ là thưởng thức ẩm thực mà còn là một nét văn hóa giao tiếp. Ốc Đào từ lâu đã khẳng định vị thế huyền thoại với nước sốt bơ tỏi thơm lừng, ốc móng tay xào rau muống giòn rụm và các món ốc hương, sò lông nướng mỡ hành.\n\nNằm trong một con hẻm trên đường Nguyễn Trãi, quán luôn tấp nập thực khách ra vào từ chiều tối. Vị cay xè của ớt hòa quyện với vị béo của bơ tỏi và vị ngọt của hải sản tươi rói sẽ khiến bất kỳ ai cũng phải xiêu lòng ngay từ lần thử đầu tiên."
  },
  {
    id: "loc-004",
    title: "Landmark 81 skyline",
    summary: "Tòa tháp biểu tượng TP.HCM – check-in, ngắm sông Sài Gòn và city view đêm.",
    image: "/images/landmark-81.jpg",
    readTime: "4 phút đọc",
    author: "Thảo Vy (Luxury Travel Guide)",
    content: "Tòa nhà cao nhất Việt Nam không chỉ là trung tâm mua sắm sầm uất mà còn là nơi sở hữu đài quan sát Skyview ở độ cao hơn 400m. Tại đây, bạn có thể ngắm nhìn dòng sông Sài Gòn uốn lượn mềm mại và toàn bộ cảnh quan thành phố chìm dần vào ánh hoàng hôn rực rỡ.\n\nBên cạnh đó, việc nhâm nhi một ly thức uống tại các lounge sang trọng ở tầng cao hoặc tản bộ trong công viên ven sông Landmark 81 dưới bóng râm của những hàng cây xanh mướt là một trải nghiệm đô thị đẳng cấp không thể bỏ qua."
  },
  {
    id: "loc-005",
    title: "Bưu điện & War Museum",
    summary: "Hai điểm văn hóa – lịch sử phải ghé khi khám phá Quận 1 Sài Gòn.",
    image: "/images/buu-dien.jpg",
    readTime: "6 phút đọc",
    author: "Alex Nguyen (History Enthusiast)",
    content: "Bưu điện Trung tâm Thành phố với kiến trúc Phục Hưng Gothic độc đáo do Gustave Eiffel thiết kế là điểm giao thoa lịch sử tuyệt đẹp. Ngay bên cạnh Nhà thờ Đức Bà, đây là nơi lưu giữ những hòm thư cổ kính và những bức bản đồ lịch sử quý giá.\n\nTiếp nối hành trình lịch sử, Bảo tàng Chứng tích Chiến tranh sẽ mang lại những cảm xúc sâu lắng về lịch sử đấu tranh kiên cường của nhân dân Việt Nam. Sự kết hợp giữa hai địa danh này mang lại một cái nhìn sâu sắc và toàn diện về quá khứ lẫn hiện tại của Sài Gòn."
  },
  {
    id: "loc-006",
    title: "Cà phê vợt Cheo Leo",
    summary: "Quán cà phê vợt có tuổi đời hơn 80 năm mang đậm nét văn hóa Sài Gòn xưa.",
    image: "https://images.unsplash.com/photo-1551631580-ff6fcd00cc9e?auto=format&fit=crop&w=800&q=80",
    readTime: "3 phút đọc",
    author: "WanderHUB Squad",
    content: "Nằm sâu trong con hẻm nhỏ ở quận 3, Cheo Leo là một trong những quán cà phê vợt hiếm hoi còn sót lại của Sài Gòn. Mùi cà phê thơm lừng quyện với không gian xưa cũ, chiếc vợt vải nhuốm màu thời gian và lò đất nung đun than củi tạo nên một trải nghiệm không thể lẫn vào đâu được.\n\nĐến đây từ sáng sớm, bạn sẽ cảm nhận được nhịp sống chậm rãi hiếm hoi của thành phố, nghe những câu chuyện đời thường từ các bậc cao niên và nhâm nhi ly 'bạc xỉu' đúng điệu."
  },
  {
    id: "loc-007",
    title: "Khu Phố Người Hoa (Chợ Lớn)",
    summary: "Thưởng thức ẩm thực Trung Hoa và khám phá kiến trúc đền chùa đặc trưng.",
    image: "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=800&q=80",
    readTime: "6 phút đọc",
    author: "Hải Đăng (Culture Explorer)",
    content: "Khu Chợ Lớn là nơi giao thoa văn hóa Việt - Hoa vô cùng độc đáo. Dạo bước qua các con phố lồng đèn đỏ, bạn sẽ bị cuốn hút bởi mùi thuốc Bắc thơm lừng, những quầy vịt quay đỏ au và các món dimsum nóng hổi.\n\nĐừng quên ghé thăm Chùa Bà Thiên Hậu - một trong những ngôi chùa cổ nhất với kiến trúc tinh xảo và hàng trăm vòng nhang vòng treo lơ lửng trên trần, tạo nên một không gian linh thiêng và đầy tính nghệ thuật."
  },
  {
    id: "loc-008",
    title: "Bảo tàng Mỹ Thuật TP.HCM",
    summary: "Kiến trúc Pháp cổ kính cùng hàng ngàn tác phẩm nghệ thuật đặc sắc.",
    image: "https://images.unsplash.com/photo-1563200989-bb0d42129e92?auto=format&fit=crop&w=800&q=80",
    readTime: "5 phút đọc",
    author: "Lan Anh (Art Enthusiast)",
    content: "Nằm trong một tòa nhà mang đậm dấu ấn kiến trúc Art Deco kết hợp Đông Dương, Bảo tàng Mỹ thuật sở hữu một không gian tĩnh lặng, tách biệt hoàn toàn với sự ồn ào bên ngoài. Hành lang ốp gạch bông rực rỡ, những ô cửa kính màu và cầu thang uốn lượn đã trở thành điểm check-in quen thuộc của giới trẻ.\n\nTuy nhiên, giá trị cốt lõi vẫn là hàng ngàn tác phẩm hội họa, điêu khắc trải dài từ mỹ thuật dân gian đến nghệ thuật đương đại Việt Nam."
  },
  {
    id: "loc-009",
    title: "Chợ Bến Thành",
    summary: "Biểu tượng giao thương lâu đời và thiên đường ẩm thực đường phố tại TP.HCM.",
    image: "/images/ben-thanh.png",
    readTime: "4 phút đọc",
    author: "WanderHUB Squad",
    content: "Chợ Bến Thành không chỉ là điểm đến mua sắm sầm uất mà còn là nơi lưu giữ những giá trị lịch sử của thành phố. Cửa Nam của chợ với tháp đồng hồ từ lâu đã trở thành biểu tượng không thể thiếu của Sài Gòn.\n\nVào ban đêm, các khu vực ẩm thực xung quanh chợ nhộn nhịp hẳn lên, cung cấp vô số món ngon đường phố từ bánh xèo, bún riêu, đến các loại chè ba màu ngọt lịm. Đây là địa điểm lý tưởng để nếm thử trọn vẹn hương vị Việt."
  },
  {
    id: "loc-010",
    title: "Bến Bạch Đằng Waterbus",
    summary: "Trải nghiệm ngắm hoàng hôn trên sông Sài Gòn cực chill với vé chỉ 15k.",
    image: "https://images.unsplash.com/photo-1583417657208-c44ebdb5e9fa?auto=format&fit=crop&w=800&q=80",
    readTime: "3 phút đọc",
    author: "Tuấn Kiệt (Local Guide)",
    content: "Không cần du thuyền đắt tiền, tuyến Waterbus số 1 từ Bến Bạch Đằng mang lại cho bạn một góc nhìn hoàn toàn khác về TP.HCM. Xuất phát từ trung tâm Quận 1, con tàu rẽ sóng đưa bạn đi ngang qua những tòa nhà chọc trời và cập bến tại các quận lân cận.\n\nThời điểm đẹp nhất để trải nghiệm là vào buổi chiều muộn (khoảng 17:00). Bạn sẽ được chiêm ngưỡng bầu trời chuyển màu rực rỡ, gió sông lồng lộng và ánh đèn thành phố bắt đầu rực sáng."
  },
  {
    id: "loc-011",
    title: "Chung cư Tôn Thất Đạm",
    summary: "Một chút hoài niệm Sài Gòn thập niên cũ giữa khu trung tâm hiện đại.",
    image: "https://images.unsplash.com/photo-1528360983277-13d401cdc186?auto=format&fit=crop&w=800&q=80",
    readTime: "4 phút đọc",
    author: "WanderHUB Squad",
    content: "Dù nằm ngay trung tâm thành phố và được bao quanh bởi các cao ốc chọc trời, chung cư Tôn Thất Đạm vẫn giữ trọn vẹn nét rêu phong, cổ kính. Những cầu thang sắt hoen rỉ, mảng tường bong tróc và không gian sinh hoạt đậm chất cư xá cũ mang đến một cảm giác hoài cổ khó tả.\n\nNơi đây còn là 'thủ phủ' của những tiệm cà phê indie, vintage clothing shop và các studio nhỏ lẩn khuất, luôn chờ đợi những tâm hồn yêu nghệ thuật đến khám phá."
  },
  {
    id: "loc-012",
    title: "Công Viên Tao Đàn",
    summary: "Lá phổi xanh mát giữa trung tâm, nơi hội tụ của chim cảnh và cà phê sáng.",
    image: "/images/tao-dan.png",
    readTime: "3 phút đọc",
    author: "Phương Trinh (Nature Lover)",
    content: "Công viên Tao Đàn với hàng ngàn cây cổ thụ rợp bóng mát là nơi lý tưởng để chạy bộ buổi sáng hoặc tản bộ thư giãn cuối tuần. Đặc biệt, khu vực cà phê chim cảnh là nét văn hóa độc đáo không thể bỏ qua.\n\nBạn có thể nhâm nhi ly cà phê đen đá, lắng nghe tiếng chim hót líu lo và quan sát nhịp sống bình dị của người dân Sài Gòn ngay giữa lòng đô thị tấp nập."
  }
];

const teamMembers = [
  {
    name: "Quỳnh Hương",
    role: "Co-founder & CEO",
    bio: "Ex-Google Maps product lead. 8 năm xây dựng sản phẩm địa điểm tại TP.HCM.",
    avatar: "/images/team/4.jpg",
  },
  {
    name: "Hồng Gấm",
    role: "Co-founder & CEO",
    bio: "Chuyên gia về chiến lược kinh doanh và phát triển sản phẩm du lịch.",
    avatar: "/images/team/3.jpg",
  },
  {
    name: "Diệu Hiền",
    role: "Co-founder & CEO",
    bio: "Người định hình tầm nhìn và sứ mệnh cốt lõi của WanderHUB.",
    avatar: "/images/team/2.jpg",
  },
  {
    name: "Bá Trọng",
    role: "Head of AI & Data",
    bio: "PhD Computer Science. Chuyên gia NLP và hệ thống gợi ý cá nhân hóa.",
    avatar: "/images/team/1.jpg",
  },
  {
    name: "Khang Phúc",
    role: "Lead UX Designer",
    bio: "Designer đến từ nền tảng boutique hospitality. Định hình trải nghiệm mượt mà.",
    avatar: "/images/team/6.jpg",
  },
  {
    name: "Quốc lơ",
    role: "Content Creator",
    bio: "Chuyên gia sáng tạo và hoạch định nội dung số. Định hình tiếng nói thương hiệu và phát triển cộng đồng người dùng.",
    avatar: "/images/team/5.jpg",
  },
];

const cityStats = [
  { value: "10.000+", label: "Người dùng thử nghiệm", sub: "Beta tại TP.HCM" },
  { value: "340+", label: "Hidden Gems", sub: "Được xác minh thực tế" },
  { value: "98%", label: "Hài lòng", sub: "Theo khảo sát beta" },
  { value: "< 3s", label: "Tạo lịch trình", sub: "Trung bình mỗi request" },
];

function Logo() {
  return (
    <NavLink id="nav-logo" to="/" className="flex items-center gap-3 decoration-0">
      <div className="h-9 w-9 overflow-hidden rounded-lg bg-[#2d5a3d]/10 p-0.5">
        <img src="/wanderhub-logo.png" alt="" />
      </div>
      <div className="leading-tight">
        <div className="text-sm font-black tracking-[0.22em] text-[#1e4230]">WANDERHUB</div>
        <div className="text-[10px] uppercase tracking-[0.24em] text-[#5a7a60]">Trải nghiệm đô thị</div>
      </div>
    </NavLink>
  );
}

const PLAN_BADGE_STYLES = {
  basic: "bg-stone-100 text-stone-600 border border-stone-200",
  premium: "bg-amber-50 text-amber-700 border border-amber-200",
  international: "bg-sky-50 text-sky-700 border border-sky-200",
};

function Navbar({ user, userPlan, onLogout }) {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-nav fixed left-4 right-4 top-4 z-50">
      <div className="nav-glass mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Logo />
        <nav className="hidden items-center gap-7 lg:flex">
          {navItems.map(([label, href]) => (
            <NavLink
              id={`nav-link-${href.replace("/", "") || "home"}`}
              key={href}
              to={href}
              className={({ isActive }) =>
                `text-sm font-medium transition ${isActive ? "text-cyan" : "text-[#5a7a60] hover:text-[#1e4230]"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          {user ? (
            <>
              <span className="text-sm font-semibold text-[#1e4230]">Chào, {user.name}!</span>
              {userPlan && (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${PLAN_BADGE_STYLES[userPlan.plan_key] || PLAN_BADGE_STYLES.basic}`}>
                  {userPlan.plan_name}
                </span>
              )}
              <button onClick={onLogout} className="btn btn-ghost">
                Đăng xuất
              </button>
            </>
          ) : (
            <>
              <NavLink id="nav-btn-login" to="/auth" className="btn btn-ghost">
                Đăng nhập
              </NavLink>
              <NavLink id="nav-btn-planner" to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn btn-primary">
                Bắt đầu lên lịch trình
              </NavLink>
            </>
          )}
        </div>
        <button id="nav-btn-hamburger" className="icon-btn lg:hidden" onClick={() => setOpen((value) => !value)} aria-label="Menu">
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {open && (
        <div className="nav-mobile mx-auto mt-3 max-w-7xl px-4 py-4 lg:hidden">
          <div className="flex flex-col gap-3">
            {[...navItems, ["FAQ", "/faq"], ["Điều khoản", "/terms"]].map(([label, href]) => (
              <NavLink
                id={`nav-mobile-link-${href.replace("/", "")}`}
                key={href}
                to={href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-3 py-2 text-[#3d2b1a]/80"
              >
                {label}
              </NavLink>
            ))}
            {user ? (
              <>
                <span className="px-3 py-2 text-sm font-semibold text-[#1e4230]">Chào, {user.name}!</span>
                <button onClick={() => { onLogout(); setOpen(false); }} className="btn btn-ghost w-full justify-center">
                  Đăng xuất
                </button>
              </>
            ) : (
              <div className="flex flex-col gap-2">
                <NavLink id="nav-mobile-btn-login" to="/auth" onClick={() => setOpen(false)} className="btn btn-ghost w-full justify-center">
                  Đăng nhập
                </NavLink>
                <NavLink id="nav-mobile-btn-planner" to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} onClick={() => setOpen(false)} className="btn btn-primary w-full justify-center">
                  Bắt đầu lên lịch trình
                </NavLink>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function Footer({ user }) {
  return (
    <footer className="border-t border-[#2d5a3d]/10 bg-[#f5f0e8]">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr] lg:px-8">
        <div>
          <Logo />
          <p className="mt-4 max-w-md text-sm leading-6 text-[#3d2b1a]/65">
            WanderHUB là người bạn thổ địa thông minh giúp bạn tìm hidden gems, xếp lịch trình và điều phối di chuyển trong thành phố.
          </p>
        </div>
        <div className="text-sm text-[#3d2b1a]/65">
          <div className="mb-3 font-semibold text-[#1e4230]">Liên hệ</div>
          <p>Địa chỉ: Thủ Đức, TP.HCM</p>
          <p>Hotline: 1900-0905</p>
          <p>Facebook: WanderHUB</p>
          <p>Instagram: Bổ sung sau</p>
        </div>
        <div className="grid gap-2 text-sm">
          <NavLink to="/faq" className="text-[#3d2b1a]/62 hover:text-cyan">FAQ</NavLink>
          <NavLink to="/terms" className="text-[#3d2b1a]/62 hover:text-cyan">Terms & Policies</NavLink>
          <NavLink to="/auth" className="text-[#3d2b1a]/62 hover:text-cyan">Login / Register</NavLink>
          <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="text-[#3d2b1a]/62 hover:text-cyan">AI Trip Planner</NavLink>
        </div>
      </div>
    </footer>
  );
}

function PageShell({ eyebrow, title, children, compact = false }) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -18 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className={`page-bg min-h-screen pt-28 ${compact ? "pb-10" : "pb-20"}`}
    >
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        {title && <h1 className="page-title">{title}</h1>}
        {children}
      </section>
    </motion.main>
  );
}

function Reveal({ children, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.65, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

const heroMessages = [
  { sub: "Landmark 81 → Nguyễn Huệ → Ốc Đào", main: ["Đi qua ánh đèn", "ven sông Sài Gòn."] },
  { sub: "AI itinerary engine", main: ["Designed For Your Vibe,", "Built For Your Route."] },
  { sub: "Bưu Điện → Secret Garden → Bến Thành", main: ["Khám phá Sài Gòn", "theo cách của bạn."] },
];

function HeroCyclingText() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIdx((i) => (i + 1) % heroMessages.length), 3600);
    return () => clearInterval(id);
  }, []);
  const { sub, main } = heroMessages[idx];
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={idx}
        initial={{ opacity: 0, y: 44 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -30 }}
        transition={{ duration: 0.72, ease: "easeOut" }}
        className="hero-cycling-slide"
      >
        <p className="eyebrow">{sub}</p>
        <h1 className="hero-title">{main[0]}<br />{main[1]}</h1>
      </motion.div>
    </AnimatePresence>
  );
}

function LaptopMockup() {
  return (
    <motion.div className="hero-stage" animate={{ rotateY: [0, -5, 5, 0], rotateX: [0, 3, -2, 0] }} transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}>
      <div className="orbit-ring" />
      <motion.div className="floating-card card-a" animate={{ y: [-8, 12, -8] }} transition={{ duration: 5, repeat: Infinity }}>
        <Sparkles size={16} /> Mood: Deadline Escape
      </motion.div>
      <motion.div className="floating-card card-b" animate={{ y: [10, -12, 10] }} transition={{ duration: 6, repeat: Infinity }}>
        <Car size={16} /> Be / Xanh SM ready
      </motion.div>
      <motion.div className="floating-card card-c" animate={{ x: [-6, 8, -6] }} transition={{ duration: 5.4, repeat: Infinity }}>
        <Gem size={16} /> Hidden gem unlocked
      </motion.div>
      <div className="laptop">
        <div className="screen">
          <div className="screen-top">
            <span />
            <strong>AI Itinerary Dashboard</strong>
            <Bot size={15} />
          </div>
          <div className="dash-grid">
            <div className="dash-panel col-span-2">
              <div className="selector-row"><span>Mood</span><b>Chill date</b></div>
              <div className="selector-row"><span>Budget</span><b>350K</b></div>
              <div className="selector-row"><span>Free time</span><b>18:30 - 22:00</b></div>
            </div>
            <div className="map-panel">
              <div className="route-line" />
              <i className="pin p1" /><i className="pin p2" /><i className="pin p3" />
            </div>
            <div className="dash-panel">
              <small>Route</small>
              <b>Cafe chill</b>
              <b>Ăn tối</b>
              <b>Check-in</b>
            </div>
            <div className="gem-card">Secret Garden<br /><span>Rooftop Q1 · SQUAD 76</span></div>
          </div>
        </div>
        <div className="base" />
      </div>
    </motion.div>
  );
}

function CinematicCarScene() {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();

    // Custom sky canvas gradient matching real Saigon starry night sky
    const skyCanvas = document.createElement("canvas");
    skyCanvas.width = 256;
    skyCanvas.height = 256;
    const skyCtx = skyCanvas.getContext("2d");
    const gradient = skyCtx.createLinearGradient(0, 0, 0, 256);
    gradient.addColorStop(0, "#030611");   // Pitch black / deep space at the top
    gradient.addColorStop(0.5, "#081026"); // Deep indigo-blue night sky
    gradient.addColorStop(1.0, "#131e3a");  // Soft glow from city light pollution at the horizon
    skyCtx.fillStyle = gradient;
    skyCtx.fillRect(0, 0, 256, 256);
    const skyTexture = new THREE.CanvasTexture(skyCanvas);
    scene.background = skyTexture;

    // Atmospheric dark indigo night fog
    scene.fog = new THREE.Fog(0x081026, 48, 120);

    const W = mount.offsetWidth || window.innerWidth;
    const H = mount.offsetHeight || window.innerHeight;

    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 300);
    camera.position.set(15, 11, 24);
    camera.lookAt(2, 2.5, -6);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x0a1128, 0.6)); // Deep dark blue ambient
    scene.add(new THREE.HemisphereLight(0x0a1931, 0x050a18, 0.7)); // Dark starry sky and ground reflection
    const sun = new THREE.DirectionalLight(0x8da9c4, 1.8); // Bright cool moonlight
    sun.position.set(-28, 24, 14);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    scene.add(sun);
    const skyFill = new THREE.DirectionalLight(0x16223f, 0.9); // Secondary cool dark fill
    skyFill.position.set(24, 18, -18);
    scene.add(skyFill);
    const landmarkGlow = new THREE.PointLight(0x00f2ff, 15, 95); // Bright Landmark cyan glow
    landmarkGlow.position.set(18, 25, -28);
    scene.add(landmarkGlow);
    const cityGlow = new THREE.PointLight(0xff9e59, 2.8, 90); // Warm neon/sodium city glow
    cityGlow.position.set(0, 3, 0);
    scene.add(cityGlow);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(140, 140),
      new THREE.MeshStandardMaterial({ color: 0x0d1117, roughness: 0.95, metalness: 0.05 }) // Very dark city ground
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const riverMat = new THREE.MeshStandardMaterial({
      color: 0x030712, // Deep black/navy river water
      roughness: 0.12,
      metalness: 0.95,
      transparent: true,
      opacity: 0.98,
    });
    const river = new THREE.Mesh(new THREE.PlaneGeometry(26, 140), riverMat);
    river.rotation.x = -Math.PI / 2;
    river.position.set(-18, 0.025, -4);
    scene.add(river);

    const riverBankMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b, // Dark concrete bank
      roughness: 0.8,
      metalness: 0.2,
    });
    [-5.1, -31.1].forEach((x) => {
      const bank = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.18, 140), riverBankMat);
      bank.position.set(x, 0.08, -4);
      bank.castShadow = true;
      bank.receiveShadow = true;
      scene.add(bank);
    });

    const riverHighlights = [];
    for (let i = 0; i < 28; i++) {
      const strip = new THREE.Mesh(
        new THREE.PlaneGeometry(0.12 + (i % 3) * 0.06, 5 + (i % 4) * 2.8),
        new THREE.MeshBasicMaterial({
          color: [0xffffff, 0xffd0a5, 0xffa15c, 0xfef08a][i % 4], // Reflecting white, warm orange, amber, and gold sunlight
          transparent: true,
          opacity: 0.52,
        })
      );
      strip.rotation.x = -Math.PI / 2;
      strip.rotation.z = 0.06;
      strip.position.set(-25 + (i % 8) * 2.1, 0.045, -52 + i * 3.8);
      strip.userData.phase = i * 0.45;
      riverHighlights.push(strip);
      scene.add(strip);
    }

    const asphaltCanvas = document.createElement("canvas");
    asphaltCanvas.width = 128;
    asphaltCanvas.height = 128;
    const asphaltCtx = asphaltCanvas.getContext("2d");
    asphaltCtx.fillStyle = "#5a5f64";
    asphaltCtx.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 900; i++) {
      const v = 8 + Math.random() * 20;
      asphaltCtx.fillStyle = `rgba(${v + 80}, ${v + 80}, ${v + 78}, ${0.06 + Math.random() * 0.12})`;
      asphaltCtx.fillRect(Math.random() * 128, Math.random() * 128, 1 + Math.random() * 1.2, 1 + Math.random() * 1.2);
    }
    const asphaltTexture = new THREE.CanvasTexture(asphaltCanvas);
    asphaltTexture.wrapS = THREE.RepeatWrapping;
    asphaltTexture.wrapT = THREE.RepeatWrapping;
    asphaltTexture.repeat.set(18, 3);

    const roadMat = new THREE.MeshStandardMaterial({
      color: 0x5a5f64,
      map: asphaltTexture,
      roughness: 0.55,
      metalness: 0.15,
    });
    const roadH = new THREE.Mesh(new THREE.PlaneGeometry(140, 7), roadMat);
    roadH.rotation.x = -Math.PI / 2;
    roadH.position.y = 0.01;
    roadH.receiveShadow = true;
    scene.add(roadH);
    const roadV = new THREE.Mesh(new THREE.PlaneGeometry(7, 140), roadMat);
    roadV.rotation.x = -Math.PI / 2;
    roadV.position.y = 0.01;
    roadV.receiveShadow = true;
    scene.add(roadV);

    const curbMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, roughness: 0.7, metalness: 0.06 });
    [-3.72, 3.72].forEach((z) => {
      const curb = new THREE.Mesh(new THREE.BoxGeometry(140, 0.16, 0.18), curbMat);
      curb.position.set(0, 0.095, z);
      curb.castShadow = true;
      curb.receiveShadow = true;
      scene.add(curb);
    });
    [-3.72, 3.72].forEach((x) => {
      const curb = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.16, 140), curbMat);
      curb.position.set(x, 0.095, 0);
      curb.castShadow = true;
      curb.receiveShadow = true;
      scene.add(curb);
    });

    const laneMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 });
    for (let i = -32; i <= 32; i += 6) {
      const dashH = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 0.06), laneMat);
      dashH.rotation.x = -Math.PI / 2;
      dashH.position.set(i, 0.075, 0);
      scene.add(dashH);
      const dashV = new THREE.Mesh(new THREE.PlaneGeometry(0.06, 2.8), laneMat);
      dashV.rotation.x = -Math.PI / 2;
      dashV.position.set(0, 0.076, i);
      scene.add(dashV);
    }

    const GRID = 9;
    const CELL = 3.2;
    const bColors = [0xdadada, 0xebebeb, 0xc0c8d0]; // Realistic warm concrete/stone building colors
    const eColors = [0x000000, 0x000000, 0x000000];
    const windows = [];
    const rng = (a, b) => ((a * 17 + b * 31) % 97) / 97;

    for (let r = 0; r < GRID; r++) {
      for (let c = 0; c < GRID; c++) {
        const cx = (c - (GRID - 1) / 2) * CELL;
        const cz = (r - (GRID - 1) / 2) * CELL;
        if (Math.abs(cx) < 3.8 || Math.abs(cz) < 3.8) continue;

        const h = 2.6 + rng(r, c) * 12;
        const bw = CELL - 0.6;
        const building = new THREE.Mesh(
          new THREE.BoxGeometry(bw, h, bw),
          new THREE.MeshStandardMaterial({
            color: bColors[(r + c) % 3],
            metalness: 0.35,
            roughness: 0.45,
            emissive: eColors[(r + c) % 3],
            emissiveIntensity: 0.0,
          })
        );
        building.position.set(cx, h / 2, cz);
        building.castShadow = true;
        building.receiveShadow = true;
        scene.add(building);

        const floors = Math.floor(h / 1.2);
        for (let f = 0; f < floors; f++) {
          for (let s = 0; s < 4; s++) {
            const isLit = rng(r * 3 + f, c * 3 + s) > 0.45; // 55% of windows starting to light up
            const wColor = isLit
              ? [0xffecc4, 0xfff0b3, 0xffdca3][(f + s) % 3] // Warm glowing yellow/orange lights inside
              : [0x82b1ff, 0x73a2ef, 0x6493de][(f + s + c) % 3]; // Light blue glass reflecting sky
            const win = new THREE.Mesh(
              new THREE.BoxGeometry(0.04, 0.28, 0.42),
              new THREE.MeshBasicMaterial({
                color: wColor,
                transparent: true,
                opacity: isLit ? 0.98 : 0.8,
              })
            );
            const angle = (s * Math.PI) / 2;
            win.position.set(
              cx + Math.cos(angle) * (bw / 2 + 0.03),
              f * 1.2 + 0.7,
              cz + Math.sin(angle) * (bw / 2 + 0.03)
            );
            win.rotation.y = angle;
            win.userData.phase = rng(r + f * 0.3, c + s * 0.5) * Math.PI * 2;
            windows.push(win);
            scene.add(win);
          }
        }
      }
    }

    const landmarkGroup = new THREE.Group();
    landmarkGroup.position.set(18, 0, -28);
    scene.add(landmarkGroup);

    const landmarkGlassGold = new THREE.MeshPhysicalMaterial({
      color: 0xffd166, // Golden yellow tint
      metalness: 0.95,
      roughness: 0.12,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
      emissive: 0x9a6a00, // Golden core glow
      emissiveIntensity: 1.2,
    });

    const landmarkGlassCyan = new THREE.MeshPhysicalMaterial({
      color: 0x00f2ff, // Bright turquoise cyan tint
      metalness: 0.98,
      roughness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      emissive: 0x0066aa, // Rich blue-cyan core glow
      emissiveIntensity: 1.5,
    });

    const LEDMat = new THREE.MeshBasicMaterial({
      color: 0x00f2ff, // Cyan LEDs starting to pop at sunset
      transparent: true,
      opacity: 0.8
    });

    // Landmark 81 stepped square columns (5x5 grid bundle)
    const heightMap = [
      [14, 18, 22, 18, 14],
      [18, 26, 30, 26, 18],
      [22, 30, 38, 30, 22],
      [18, 26, 30, 26, 18],
      [14, 18, 22, 18, 14],
    ];

    const colW = 0.55;
    const colGap = 0.05;
    const step = colW + colGap;

    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        // Omit outer corners to match stepped square profile
        if ((r === 0 || r === 4) && (c === 0 || c === 4)) continue;

        const h = heightMap[r][c];
        const cx = (c - 2) * step;
        const cz = (r - 2) * step;

        if (h > 18) {
          // Lower segment (Gold glow)
          const hLower = 18;
          const colGeomLower = new THREE.BoxGeometry(colW, hLower, colW);
          const colMeshLower = new THREE.Mesh(colGeomLower, landmarkGlassGold);
          colMeshLower.position.set(cx, hLower / 2, cz);
          colMeshLower.castShadow = true;
          colMeshLower.receiveShadow = true;
          landmarkGroup.add(colMeshLower);

          // Upper segment (Cyan glow)
          const hUpper = h - 18;
          const colGeomUpper = new THREE.BoxGeometry(colW, hUpper, colW);
          const colMeshUpper = new THREE.Mesh(colGeomUpper, landmarkGlassCyan);
          colMeshUpper.position.set(cx, 18 + hUpper / 2, cz);
          colMeshUpper.castShadow = true;
          colMeshUpper.receiveShadow = true;
          landmarkGroup.add(colMeshUpper);
        } else {
          // Entire column is lower height (Gold glow)
          const colGeom = new THREE.BoxGeometry(colW, h, colW);
          const colMesh = new THREE.Mesh(colGeom, landmarkGlassGold);
          colMesh.position.set(cx, h / 2, cz);
          colMesh.castShadow = true;
          colMesh.receiveShadow = true;
          landmarkGroup.add(colMesh);
        }

        // Vertical glowing LED lines on corners
        const edgeOffset = colW / 2 + 0.02;
        const corners = [
          [-edgeOffset, -edgeOffset],
          [edgeOffset, -edgeOffset],
          [edgeOffset, edgeOffset],
          [-edgeOffset, edgeOffset],
        ];

        corners.forEach(([ex, ez]) => {
          const ledGeom = new THREE.BoxGeometry(0.06, h, 0.06);
          const led = new THREE.Mesh(ledGeom, LEDMat);
          led.position.set(cx + ex, h / 2, cz + ez);
          landmarkGroup.add(led);
        });
      }
    }

    // Tall spire on top of the central column
    const spireH = 12;
    const spireGeom = new THREE.CylinderGeometry(0.03, 0.15, spireH, 6);
    const spireMat = new THREE.MeshStandardMaterial({
      color: 0xf1f5f9,
      metalness: 0.95,
      roughness: 0.05,
      emissive: 0xbae6fd,
      emissiveIntensity: 0.4
    });
    const spire = new THREE.Mesh(spireGeom, spireMat);
    spire.position.set(0, 38 + spireH / 2, 0);
    landmarkGroup.add(spire);

    // Blinking beacon light at the tip of the spire
    const beacon = new THREE.Mesh(
      new THREE.SphereGeometry(0.15, 8, 8),
      new THREE.MeshBasicMaterial({ color: 0xff0033 })
    );
    beacon.position.set(0, 38 + spireH, 0);
    landmarkGroup.add(beacon);

    const beaconLight = new THREE.PointLight(0xff0033, 1, 15);
    beaconLight.position.set(0, 38 + spireH, 0);
    landmarkGroup.add(beaconLight);

    // Glowing horizontal decorative rings
    for (let i = 1; i <= 6; i++) {
      const ringH = i * 6;
      const ringGeom = new THREE.BoxGeometry(3.1, 0.08, 3.1);
      const ringMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.9, roughness: 0.1 });
      const ring = new THREE.Mesh(ringGeom, ringMat);
      ring.position.set(0, ringH, 0);
      landmarkGroup.add(ring);
    }

    const routeCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-7.5, 0.1, -38),
      new THREE.Vector3(-2.5, 0.1, -24),
      new THREE.Vector3(4.5, 0.1, -13),
      new THREE.Vector3(1.5, 0.1, 1),
      new THREE.Vector3(-5.5, 0.1, 15),
      new THREE.Vector3(2.5, 0.1, 31),
    ]);
    const routeLineMat = new THREE.MeshBasicMaterial({ color: 0x2d5a3d, transparent: true, opacity: 0.85 });
    const routeLine = new THREE.Mesh(new THREE.TubeGeometry(routeCurve, 180, 0.055, 8, false), routeLineMat);
    scene.add(routeLine);

    const railMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.4, metalness: 0.5 });
    for (let z = -54; z <= 54; z += 3.2) {
      const railPost = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.7, 0.07), railMat);
      railPost.position.set(-5.55, 0.38, z);
      railPost.castShadow = true;
      scene.add(railPost);
    }
    [0.42, 0.72].forEach((y) => {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 112), railMat);
      rail.position.set(-5.55, y, 0);
      rail.castShadow = true;
      scene.add(rail);
    });

    const lampPosts = [];
    const lampMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.35, metalness: 0.72 });
    const lampGlowMat = new THREE.MeshBasicMaterial({ color: 0xfffee0, transparent: true, opacity: 0.92 });
    for (let i = 0; i < 16; i++) {
      const z = -46 + i * 6.1;
      const x = i % 2 === 0 ? -4.3 : 4.3;
      const post = new THREE.Group();
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.05, 2.4, 8), lampMat);
      stem.position.y = 1.2;
      stem.castShadow = true;
      post.add(stem);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.045, 0.045), lampMat);
      arm.position.set(x < 0 ? 0.34 : -0.34, 2.3, 0);
      post.add(arm);
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.13, 12, 8), lampGlowMat);
      bulb.position.set(x < 0 ? 0.72 : -0.72, 2.25, 0);
      post.add(bulb);
      const lampLight = new THREE.PointLight(0xffbf69, 1.2, 5.0); // Vibrant sodium streetlamp glow
      lampLight.position.copy(bulb.position);
      post.add(lampLight);
      post.position.set(x, 0, z);
      lampPosts.push(post);
      scene.add(post);
    }

    const treeTrunkMat = new THREE.MeshStandardMaterial({ color: 0x653b1b, roughness: 0.85 });
    const treeLeafMat = new THREE.MeshStandardMaterial({ color: 0x16a34a, roughness: 0.75, emissive: 0x15803d, emissiveIntensity: 0.05 });
    for (let i = 0; i < 18; i++) {
      const tree = new THREE.Group();
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 0.95, 7), treeTrunkMat);
      trunk.position.y = 0.48;
      tree.add(trunk);
      const crown = new THREE.Mesh(new THREE.SphereGeometry(0.48 + (i % 3) * 0.08, 10, 8), treeLeafMat);
      crown.position.y = 1.12;
      crown.scale.set(1.1, 0.78, 1);
      tree.add(crown);
      tree.position.set(i % 2 ? -7.2 : 6.2, 0, -50 + i * 5.8);
      tree.rotation.y = i * 0.41;
      scene.add(tree);
    }

    // Road loop helper — position sweeps -L to +L and wraps
    const roadLoop = (t, speed, phase = 0, L = 18) => {
      const len = L * 2;
      return ((t * speed + phase * len) % len + len) % len - L;
    };

    // All car groups use the same rotation convention:
    //   inner.rotation.y = Math.PI  → car visual faces -Z in parent space
    //   parent.rotation.y = PI/2    → car faces +X in world
    //   parent.rotation.y = -PI/2   → car faces -X
    //   parent.rotation.y = PI      → car faces +Z
    //   parent.rotation.y = 0       → car faces -Z
    const makeTrafficCar = (bodyColor, glowColor) => {
      const g = new THREE.Group();
      const inner = new THREE.Group();
      inner.rotation.y = Math.PI; // same convention as GLB model
      g.add(inner);
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(1.5, 0.44, 2.7),
        new THREE.MeshStandardMaterial({ color: bodyColor, metalness: 0.55, roughness: 0.28 })
      );
      body.position.y = 0.44;
      inner.add(body);
      const cabin = new THREE.Mesh(
        new THREE.BoxGeometry(1.1, 0.4, 1.0),
        new THREE.MeshStandardMaterial({ color: 0xd8f0f8, transparent: true, opacity: 0.48, metalness: 0.05, roughness: 0.04 })
      );
      cabin.position.set(0, 0.88, 0.08);
      inner.add(cabin);
      const pt = new THREE.PointLight(glowColor, 0.2, 6);
      pt.position.y = 0.1;
      g.add(pt);
      return g;
    };

    // Main car (GLB + fallback) — always on horizontal road, right lane
    const carGroup = new THREE.Group();
    scene.add(carGroup);

    // fallbackGroup uses same inner-rotation convention as GLB (model.rotation.y = PI)
    const fallbackGroup = new THREE.Group();
    fallbackGroup.rotation.y = Math.PI;
    carGroup.add(fallbackGroup);

    const bodyMesh = new THREE.Mesh(
      new THREE.BoxGeometry(1.8, 0.55, 3.2),
      new THREE.MeshStandardMaterial({ color: 0xc96420, metalness: 0.65, roughness: 0.2 })
    );
    bodyMesh.position.y = 0.5;
    fallbackGroup.add(bodyMesh);

    const cabinMesh = new THREE.Mesh(
      new THREE.BoxGeometry(1.3, 0.52, 1.2),
      new THREE.MeshStandardMaterial({ color: 0xd8f0f8, transparent: true, opacity: 0.55, metalness: 0.05, roughness: 0.04 })
    );
    cabinMesh.position.set(0, 1.05, 0.1);
    fallbackGroup.add(cabinMesh);

    const stripMat = new THREE.MeshStandardMaterial({ color: 0xc96420 });
    for (const sx of [-0.91, 0.91]) {
      const strip = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.055, 2.9), stripMat);
      strip.position.set(sx, 0.72, 0);
      fallbackGroup.add(strip);
    }

    const headlightMat = new THREE.MeshBasicMaterial({ color: 0xfff3c9, transparent: true, opacity: 0.86 });
    for (const sx of [-0.42, 0.42]) {
      const headlight = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.05), headlightMat);
      headlight.position.set(sx, 0.58, -1.62);
      fallbackGroup.add(headlight);
    }

    const carGlow = new THREE.PointLight(0xffca3a, 1.2, 8); // Warm gold underglow
    carGlow.position.y = 0.12;
    carGroup.add(carGlow);
    const headLightLeft = new THREE.SpotLight(0xfff0c8, 1.8, 14, 0.34, 0.65, 1.4); // Strong warm headlights
    headLightLeft.position.set(-0.45, 0.7, -1.4);
    headLightLeft.target.position.set(-0.75, 0.05, -7);
    carGroup.add(headLightLeft);
    carGroup.add(headLightLeft.target);
    const headLightRight = headLightLeft.clone();
    headLightRight.position.set(0.45, 0.7, -1.4);
    headLightRight.target = new THREE.Object3D();
    headLightRight.target.position.set(0.75, 0.05, -7);
    carGroup.add(headLightRight);
    carGroup.add(headLightRight.target);

    // Use fallback car group directly (which renders perfectly and avoids GLB rotation bugs)
    fallbackGroup.visible = true;

    // Traffic cars on the cross roads (staying inside the road corridors)
    // ax='h' → horizontal road (z = lane), ax='v' → vertical road (x = lane)
    // spd>0 → positive direction (+X or +Z), spd<0 → negative
    const trafficConfig = [
      { bodyC: 0x3a7a52, glowC: 0x7fb08a, ax: 'h', spd: -4.5, lane: 1.5, ph: 0.2 },
      { bodyC: 0xd4721e, glowC: 0xffa040, ax: 'v', spd: 4.8, lane: 1.5, ph: 0.5 },
      { bodyC: 0xb04030, glowC: 0xff8060, ax: 'v', spd: -4.0, lane: -1.5, ph: 0.75 },
      { bodyC: 0x4488cc, glowC: 0x88ccff, ax: 'h', spd: 5.5, lane: -1.5, ph: 0.45 },
    ];
    const trafficCars = trafficConfig.map(({ bodyC, glowC, ax, spd, lane, ph }) => ({
      car: makeTrafficCar(bodyC, glowC), ax, spd, lane, ph,
    }));
    trafficCars.forEach(({ car }) => scene.add(car));

    const clock = new THREE.Clock();
    let raf;

    const onResize = () => {
      const w = mount.offsetWidth || window.innerWidth;
      const h = mount.offsetHeight || window.innerHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    const animate = () => {
      raf = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      const progress = (t * 0.052) % 1;
      const carPoint = routeCurve.getPointAt(progress);
      const tangent = routeCurve.getTangentAt(progress);
      carGroup.position.copy(carPoint);
      carGroup.position.y = 0.16 + Math.sin(t * 2.2) * 0.035;
      carGroup.rotation.y = Math.atan2(tangent.x, -tangent.z);
      carGroup.rotation.z = Math.sin(t * 1.8) * 0.018;
      carGroup.rotation.x = -Math.sin(progress * Math.PI * 2) * 0.018;
      routeLine.material.opacity = 0.58 + Math.sin(t * 1.4) * 0.18;

      // Traffic cars — on cross roads, never through buildings
      trafficCars.forEach(({ car, ax, spd, lane, ph }) => {
        const pos = roadLoop(t, Math.abs(spd), ph);
        const dir = Math.sign(spd);
        if (ax === 'h') {
          car.position.x = pos * dir;
          car.position.z = lane;
          // dir>0 → +X (rot PI/2), dir<0 → -X (rot -PI/2)
          car.rotation.y = dir > 0 ? Math.PI / 2 : -Math.PI / 2;
        } else {
          car.position.x = lane;
          car.position.z = pos * dir;
          // dir>0 → +Z (rot PI), dir<0 → -Z (rot 0)
          car.rotation.y = dir > 0 ? Math.PI : 0;
        }
        car.position.y = 0.1;
      });

      const followOffset = new THREE.Vector3(13 + Math.sin(t * 0.22) * 2, 8.5, 18);
      camera.position.lerp(carPoint.clone().add(followOffset), 0.055);
      camera.lookAt(carPoint.x + 3.2, carPoint.y + 2.1, carPoint.z - 8);

      windows.forEach((win) => {
        win.material.opacity = 0.48 + Math.sin(t * 0.85 + win.userData.phase) * 0.28;
      });
      riverHighlights.forEach((strip) => {
        strip.material.opacity = 0.12 + Math.sin(t * 0.72 + strip.userData.phase) * 0.08;
      });

      // Blinking red aviation warning beacon at the top of Landmark 81 spire
      if (beacon && beaconLight) {
        const isBeaconOn = Math.sin(t * 7.5) > 0.25;
        beaconLight.intensity = isBeaconOn ? 3.5 : 0.0;
        beacon.material.color.setHex(isBeaconOn ? 0xff0033 : 0x3d0008);
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  return <div ref={mountRef} className="scroll-car-scene" aria-hidden="true" />;
}

function CinematicRouteOverlay() {
  return (
    <div className="journey-overlay" aria-hidden="true">
      <svg className="journey-route-svg" viewBox="0 0 420 980" preserveAspectRatio="none">
        <defs>
          <linearGradient id="journeyRouteGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7fb08a" />
            <stop offset="52%" stopColor="#2d5a3d" />
            <stop offset="100%" stopColor="#c96420" />
          </linearGradient>
        </defs>
        <path className="journey-route-shadow" d="M184 12 C 332 172 72 292 220 442 C 340 560 86 702 210 968" />
        <path className="journey-route-active auto-route-line" d="M184 12 C 332 172 72 292 220 442 C 340 560 86 702 210 968" />
      </svg>

      <JourneyStopCard
        className="stop-cafe"
        icon={Coffee}
        label="Stop 01"
        title="Phố Nguyễn Huệ"
        text="Cafe chill trên trục kết nối trung tâm Q1."
        delay={0.4}
      />
      <JourneyStopCard
        className="stop-dinner"
        icon={Utensils}
        label="Stop 02"
        title="Ốc Đào"
        text="Ăn tối seafood local – điểm 87 SQUAD."
        delay={1.4}
      />
      <JourneyStopCard
        className="stop-gem"
        icon={MapPin}
        label="Stop 03"
        title="Secret Garden"
        text="Rooftop ẩn giữa Q1 – hidden gem đúng nghĩa."
        delay={2.4}
      />
      <JourneyStopCard
        className="stop-checkin"
        icon={Camera}
        label="Stop 04"
        title="Landmark 81"
        text="Check-in skyline Sài Gòn từ tòa tháp biểu tượng."
        delay={3.2}
      />

      <motion.div
        className="journey-final-cta"
        initial={{ opacity: 0, x: "-50%", y: 24 }}
        animate={{ opacity: [0, 1, 1, 0], x: "-50%", y: [24, 0, 0, -10] }}
        transition={{ duration: 7.5, delay: 3.8, repeat: Infinity, repeatDelay: 0.4, ease: "easeInOut" }}
      >
        <span>Final destination</span>
        <strong>Lịch trình đã sẵn sàng</strong>
      </motion.div>
    </div>
  );
}

function JourneyStopCard({ className, icon: Icon, label, title, text, delay }) {
  return (
    <motion.div
      className={`journey-stop-card ${className}`}
      initial={{ opacity: 0, y: 28, scale: 0.94 }}
      animate={{ opacity: [0, 1, 1, 0], y: [28, 0, -4, -18], scale: [0.94, 1, 1, 0.98] }}
      transition={{ duration: 6.8, delay, repeat: Infinity, repeatDelay: 1.4, ease: "easeInOut" }}
    >
      <div className="journey-stop-icon">
        <Icon size={18} />
      </div>
      <div>
        <span>{label}</span>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </motion.div>
  );
}

// ── FLOATING CHATBOT KNOWLEDGE (Layer 4 - AI Conversation Layer) ──
const csKnowledge = [
  {
    kw: ["chill", "quận 1", "tối nay"],
    ans: "Với thời tiết mưa nhẹ và ngân sách khoảng 300k, bạn có thể đi theo tuyến:\n**Đường sách Nguyễn Văn Bình** → **Saigon Centre** → **Cafe Apartment**.\nCác địa điểm này gần nhau, phù hợp đi bộ nhẹ và tránh di chuyển quá xa trong thời tiết hiện tại. Bạn có muốn đổi điểm nào không?"
  },
  {
    kw: ["landmark 81", "gần landmark", "bình thạnh"],
    ans: "Gần khu vực Landmark 81, hệ thống gợi ý bạn có thể dạo bộ ở **Công viên Landmark** ven sông. Nếu muốn không gian trên cao, **Blank Lounge** (Tầng 75) hoặc **Ussina** (Tầng 77) là lựa chọn tuyệt vời. Bạn cần tôi kiểm tra giờ mở cửa của điểm nào?"
  },
  {
    kw: ["plan", "lịch trình", "half-day", "tour", "tạo lịch"],
    ans: "Để tạo một lịch trình custom hoàn chỉnh (kèm tối ưu quãng đường và gợi ý đặt xe), bạn hãy sử dụng tính năng **Lên Lịch Trình (AI Planner)** của WanderHUB nhé. \n\nTại đây, tôi chỉ có thể gợi ý nhanh một vài địa điểm. Bạn muốn đến khu vực nào?"
  },
  {
    kw: ["bỏ", "đổi", "xóa", "không thích"],
    ans: "Đã ghi nhận! Tôi có thể thay thế địa điểm đó bằng một lựa chọn khác phù hợp hơn với bạn. Bạn thích không gian ngoài trời hay trong nhà thay thế vào chỗ đó?"
  },
  {
    kw: ["romantic", "lãng mạn", "budget thấp", "rẻ"],
    ans: "Dựa trên dữ liệu, nếu bạn tìm không gian lãng mạn với ngân sách vừa phải, **Secret Garden Rooftop** (Pasteur, Q1) là một hidden gem rất phù hợp: không gian xanh, ấm cúng và riêng tư. Tôi có thể giải thích thêm về menu nếu bạn cần."
  },
  {
    kw: ["hủy", "cancel", "hoàn tiền", "refund", "premium", "gói", "giá"],
    ans: "Về dịch vụ khách hàng:\n• Gói **Premium** có giá 89.000 VNĐ/tháng.\n• Bạn có thể hủy gói bất kỳ lúc nào.\n• Chính sách hoàn tiền 100% áp dụng trong 7 ngày đầu tiên sử dụng.\nBạn cần hỗ trợ gì thêm về tài khoản không?"
  },
  {
    kw: ["liên hệ", "hotline", "support", "hỗ trợ"],
    ans: "Đội ngũ CSKH của WanderHUB luôn sẵn sàng:\n• Hotline: **1900-0905** (8h-22h)\n• Hoặc bạn có thể để lại lời nhắn ở trang **Liên hệ**.\nTôi có thể giúp bạn giải đáp ngay thông tin gì từ hệ thống không?"
  }
];

const csQuickReplies = [
  "Tối nay đi đâu chill ở Q1?",
  "Có chỗ nào gần Landmark 81 không?",
  "Tôi muốn ăn tối romantic budget thấp",
  "Hỗ trợ hoàn tiền / Hủy gói",
];

function FloatingChatBot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { from: "ai", text: "Xin chào! Tôi là WanderBot của WanderHUB. \n\nTôi ở đây để diễn giải các đề xuất điểm đến, hỗ trợ điều chỉnh hành trình và giải đáp thông tin dịch vụ (CSKH) cho bạn. Tôi có thể giúp gì cho bạn hôm nay?" }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [unread, setUnread] = useState(1);
  const [groqKey, setGroqKey] = useState(localStorage.getItem('wanderhub_groq_key') || import.meta.env.VITE_GROQ_API_KEY || "");
  const [showSettings, setShowSettings] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const openChat = () => {
    setOpen(true);
    setUnread(0);
  };

  const saveKey = (e) => {
    const val = e.target.value;
    setGroqKey(val);
    localStorage.setItem('wanderhub_groq_key', val);
  };

  const getReply = (text) => {
    const lower = text.toLowerCase();
    for (const item of csKnowledge) {
      if (item.kw.some((k) => lower.includes(k))) return item.ans;
    }
    return `Cảm ơn bạn đã liên hệ! 🙏\n\nTôi chưa có thông tin chính xác về câu hỏi này. Vui lòng:\n• Gọi hotline **1900-0905** (8h-22h)\n• Nhắn tin Facebook **WanderHUB**\n• Hoặc để lại tin nhắn qua trang **Liên hệ**\n\nĐội ngũ sẽ phản hồi trong vòng 1 giờ!`;
  };

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg) return;
    
    const newMessages = [...messages, { from: "user", text: msg }];
    setMessages(newMessages);
    setInput("");
    setIsTyping(true);

    try {
      const aiReply = await processUserMessage(msg, newMessages, groqKey || null);
      setIsTyping(false);
      setMessages((p) => [...p, { from: "ai", text: aiReply }]);
    } catch (err) {
      setIsTyping(false);
      setMessages((p) => [...p, { from: "ai", text: `Lỗi kết nối AI Engine: ${err.message}` }]);
    }
  };

  const renderText = (text) =>
    text.split("\n").map((line, i) => (
      <span key={i}>
        {line.split(/\*\*(.+?)\*\*/).map((part, j) =>
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )}
        <br />
      </span>
    ));

  return (
    <div className="wb-root">
      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.95 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="wb-panel"
          >
            {/* Header */}
            <div className="wb-header">
              <div className="flex items-center gap-3">
                <div className="wb-avatar">
                  <Bot size={16} className="text-white" />
                </div>
                <div>
                  <div className="wb-title">WanderBot {groqKey ? "(Groq Live)" : "(Mock)"}</div>
                  <div className="wb-status">
                    <span className="wb-dot" />Hỗ trợ khách hàng
                  </div>
                </div>
              </div>
              <div className="flex gap-2 items-center">
                <button onClick={() => setShowSettings(!showSettings)} className="wb-close" title="Cài đặt API">
                  <Settings size={16} />
                </button>
                <button onClick={() => setOpen(false)} className="wb-close">
                  <X size={16} />
                </button>
              </div>
            </div>

            {showSettings && (
              <div className="p-3 bg-stone-100 border-b border-stone-200">
                <label className="text-xs font-bold text-stone-600 mb-1 block">Groq API Key (Tùy chọn)</label>
                <input 
                  type="password"
                  value={groqKey}
                  onChange={saveKey}
                  placeholder="gsk_..."
                  className="w-full text-xs p-2 rounded border border-stone-300 outline-none"
                />
                <p className="text-[10px] text-stone-500 mt-1 leading-tight">Nếu không nhập, bot sẽ chạy ở chế độ Mock Data mô phỏng.</p>
              </div>
            )}

            {/* Messages */}
            <div className="wb-messages">
              {messages.map((msg, i) => (
                <div key={i} className={`wb-bubble-row ${msg.from}`}>
                  {msg.from === "ai" && (
                    <div className="wb-bot-icon"><Bot size={12} /></div>
                  )}
                  <div className={`wb-bubble ${msg.from}`}>
                    {renderText(msg.text)}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="wb-bubble-row ai">
                  <div className="wb-bot-icon"><Bot size={12} /></div>
                  <div className="wb-bubble ai">
                    <span className="wb-typing"><span/><span/><span/></span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Quick replies */}
            <div className="wb-quick-replies">
              {csQuickReplies.map((q) => (
                <button key={q} onClick={() => send(q)} className="wb-chip">{q}</button>
              ))}
            </div>

            {/* Input */}
            <div className="wb-input-row">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Nhắp câu hỏi..."
                className="wb-input"
              />
              <button onClick={() => send()} className="wb-send">
                <ArrowRight size={16} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bubble trigger */}
      <motion.button
        onClick={openChat}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        className="wb-bubble-btn"
        aria-label="Mở hỗ trợ"
      >
        <Bot size={24} />
        {unread > 0 && !open && (
          <span className="wb-badge">{unread}</span>
        )}
      </motion.button>
    </div>
  );
}


function Home({ user }) {

  return (
    <motion.main initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="overflow-hidden bg-[#fdf8f3]">
      
      {/* SECTION 1: HERO */}
      <section className="journey-hero cinematic-auto-hero">
        <div className="journey-sticky">
          <div className="journey-aurora" />
          <div className="journey-city-grid" />
          <CinematicCarScene />

          <div className="hero-center-content">
            <div className="hero-cycling-wrapper">
              <HeroCyclingText />
            </div>
            <p className="hero-city-description">
              Góc nhìn WanderHUB đồng hành cùng bạn trên hành trình khám phá thành phố: lướt qua tuyến ven sông Sài Gòn,
              ngắm Landmark 81 phản chiếu trên mặt nước dưới ánh nắng ấm áp, nối tiếp các điểm cafe, ăn tối và check-in
              đúng gu của bạn.
            </p>
            <div className="flex gap-4 mt-8 pointer-events-auto">
              <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn btn-primary hero-main-cta">
                Lên lịch trình ngay <ArrowRight size={18} />
              </NavLink>
              <button 
                onClick={() => document.getElementById("experience-section")?.scrollIntoView({ behavior: "smooth" })}
                className="btn btn-glass hero-main-cta"
              >
                Xem Trải Nghiệm Đô Thị
              </button>
            </div>
          </div>

          <motion.div
            className="ai-itinerary-card"
            initial={{ opacity: 0, y: 36 }}
            animate={{ opacity: [0, 1, 1, 0.72, 1], y: [36, 0, 0, -8, 0] }}
            transition={{ duration: 8, delay: 1.1, repeat: Infinity, repeatDelay: 0.6, ease: "easeInOut" }}
          >
            <div className="flex items-center justify-between gap-3">
              <span>AI ITINERARY RECOMMENDED</span>
              <Bot size={18} />
            </div>
            <strong className="text-stone-800">Route: Q1 Urban Vibe</strong>
            <div className="ai-itinerary-steps">
              <p><Coffee size={14} /> Cafe · Phố Nguyễn Huệ</p>
              <p><Utensils size={14} /> Ốc Đào · Q1 Seafood</p>
              <p><Car size={14} /> Check-in · Landmark 81</p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* SECTION 2: PLATFORM FEATURES */}
      <section className="editorial-section bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="section-eyebrow">Nền tảng WanderHUB</span>
            <h2 className="section-title-large">Ba bước – Một hành trình.</h2>
            <p className="text-stone-600">Từ khi chọn mood đến khi bước xuống xe, WanderHUB lo hết.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                icon: Sparkles,
                title: "Chọn mood & vibe",
                desc: "Chỉ mất 30 giây – chọn cảm xúc, thời gian rảnh và ngân sách bạn muốn chi hôm nay.",
                color: "#c96420",
              },
              {
                step: "02",
                icon: Bot,
                title: "AI dựng lịch trình",
                desc: "WanderHUB AI tối ưu hóa tuyến đường, chọn địa điểm đúng vị trí và kết nối xe điện đồng bộ.",
                color: "#2d5a3d",
              },
              {
                step: "03",
                icon: Car,
                title: "Lên đường thôi!",
                desc: "Có Xanh SM đợi sẵn, lịch trình hiển thị realtime. Bạn chỉ cần xuất hiện đông giờ.",
                color: "#1e4230",
              }
            ].map(({ step, icon: Icon, title, desc, color }) => (
              <Reveal key={step} className="relative p-8 rounded-2xl border border-stone-100 bg-[#fdf8f3] hover:shadow-lg transition">
                <div className="text-6xl font-black absolute top-4 right-6" style={{ color: `${color}12` }}>{step}</div>
                <div className="h-12 w-12 rounded-xl flex items-center justify-center mb-6" style={{ background: `${color}15` }}>
                  <Icon size={24} style={{ color }} />
                </div>
                <h3 className="text-xl font-bold text-[#1e4230] mb-2">{title}</h3>
                <p className="text-sm text-stone-600 leading-relaxed">{desc}</p>
              </Reveal>
            ))}
          </div>
          <div className="text-center mt-10">
            <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn btn-primary inline-flex items-center gap-2">
              Thử tạo lịch trình ngay <ArrowRight size={16} />
            </NavLink>
          </div>
        </div>
      </section>

      {/* SECTION 3: ABOUT WANDERHUB */}
      <section className="editorial-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <Reveal>
              <span className="section-eyebrow">Thương hiệu WanderHUB</span>
              <h2 className="section-title-large">Một góc nhìn lịch lãm về khám phá đô thị.</h2>
              <p className="text-stone-600 leading-relaxed mb-6">
                Chúng tôi tin rằng việc du ngoạn quanh thành phố Hồ Chí Minh không đơn giản là đi từ A đến B. Đó là sự khám phá
                những ngóc ngách ẩn giấu, thưởng thức ly cà phê phin đúng điệu và cảm nhận nhịp đập năng động của Sài Gòn.
              </p>
              <p className="text-stone-600 leading-relaxed mb-6">
                Bằng sự kết hợp giữa trí tuệ nhân tạo thông minh và kiến thức bản địa sâu sắc, WanderHUB tối ưu hóa từng tuyến đường di chuyển,
                giúp bạn tiết kiệm thời gian mà vẫn tận hưởng trọn vẹn những điểm đến tinh tế nhất.
              </p>
              <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn btn-primary">
                Trải Nghiệm Ngay <ChevronRight size={16} />
              </NavLink>
            </Reveal>
            <Reveal>
              <div className="gallery-card shadow-2xl">
                <img src="/images/landmark-81.jpg" alt="Landmark 81 skyline" className="gallery-img" />
                <div className="gallery-overlay-dark">
                  <h3 className="serif-h text-white text-2xl mb-1">Landmark 81</h3>
                  <p className="text-white/80 text-sm">Biểu tượng tự hào của TP. Hồ Chí Minh hiện đại</p>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* SECTION 4: AI FEATURES */}
      <section className="editorial-section bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="section-eyebrow">AI-Powered Experience</span>
            <h2 className="section-title-large">Trí tuệ nhân tạo hỗ trợ khám phá</h2>
            <p className="text-stone-600">Những mảnh ghép công nghệ tạo nên một chuyến đi trọn vẹn và không lo toan.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: "Tối ưu hóa tuyến đường AI",
                desc: "AI sắp xếp thứ tự các điểm dừng hợp lý nhất để giảm thiểu kẹt xe và rút ngắn thời gian di chuyển đô thị.",
                icon: RouteIcon
              },
              {
                title: "Tích hợp chuyến đi thông minh",
                desc: "Kết nối trực tiếp dịch vụ đặt xe điện Xanh SM và các đơn vị uy tín giúp bạn đi lại êm ái, bảo vệ môi trường.",
                icon: Navigation
              },
              {
                title: "Gợi ý Hidden Gems",
                desc: "Kho dữ liệu bản địa chọn lọc giới thiệu những quán cà phê chung cư cũ, quán ăn vỉa hè chuẩn vị ít người biết.",
                icon: Gem
              },
              {
                title: "Cập nhật đô thị Realtime",
                desc: "Theo dõi tình hình thời tiết và lưu lượng giao thông trực tiếp để đề xuất re-route tức thời khi cần.",
                icon: Clock3
              },
              {
                title: "Cá nhân hóa trải nghiệm",
                desc: "Lịch trình tự động điều chỉnh theo mức ngân sách của bạn (từ bình dân đến cao cấp) và vibe buổi hẹn.",
                icon: Bot
              },
              {
                title: "Trợ lý ảo thông minh",
                desc: "Trò chuyện trực tiếp cùng trợ lý để nhận thêm thông tin điểm đến hoặc đổi điểm dừng trong nháy mắt.",
                icon: Sparkles
              }
            ].map((feat, idx) => {
              const Icon = feat.icon;
              return (
                <Reveal key={idx} className="p-8 rounded-2xl border border-stone-100 bg-[#fdf8f3] hover:shadow-lg transition">
                  <div className="h-12 w-12 rounded-xl bg-[#2d5a3d]/10 flex items-center justify-between p-3 text-[#2d5a3d] mb-6">
                    <Icon size={24} />
                  </div>
                  <h3 className="text-xl font-bold text-[#1e4230] mb-3">{feat.title}</h3>
                  <p className="text-sm text-stone-600 leading-relaxed">{feat.desc}</p>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTION 5: CURATED EXPERIENCES */}
      <section id="experience-section" className="editorial-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="section-eyebrow">Curated Vibe Spots</span>
            <h2 className="section-title-large">Trải nghiệm Sài Gòn tuyển chọn</h2>
            <p className="text-stone-600">Được sắp xếp và cập nhật liên tục bởi WanderHUB SQUAD.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: "Secret Garden Rooftop",
                desc: "Không gian ẩm thực Việt mộc mạc, tĩnh lặng trên sân thượng chung cư cũ Pasteur.",
                badge: "Rooftop Café",
                img: "/images/secret-garden.png",
                rating: "4.9"
              },
              {
                title: "Ốc Đào Q1",
                desc: "Trải nghiệm ẩm thực hải sản đường phố Sài Gòn trứ danh với vị bơ tỏi thơm lừng.",
                badge: "Local Food",
                img: "/images/oc-dao.png",
                rating: "4.8"
              },
              {
                title: "Bến Bạch Đằng & River View",
                desc: "Đi bộ đón gió sông mát lành ngắm nhìn Landmark 81 lung linh ánh đèn hoàng hôn.",
                badge: "Riverside",
                img: "/images/landmark-81-3d.png",
                rating: "4.9"
              }
            ].map((exp, idx) => (
              <Reveal key={idx}>
                <div className="exp-card">
                  <div className="exp-image-wrapper">
                    <img src={exp.img} alt={exp.title} className="exp-img" />
                    <span className="exp-badge">{exp.badge}</span>
                  </div>
                  <div className="p-6 flex-1 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-xl font-bold text-[#1e4230]">{exp.title}</h4>
                        <span className="text-sm font-semibold text-[#c96420] flex items-center gap-1">
                          <Star size={14} fill="currentColor" /> {exp.rating}
                        </span>
                      </div>
                      <p className="text-sm text-stone-600 leading-relaxed mb-6">{exp.desc}</p>
                    </div>
                    <NavLink to="/explore" className="text-sm font-bold text-[#2d5a3d] hover:text-[#c96420] inline-flex items-center gap-1 self-start transition">
                      Tìm hiểu thêm <ChevronRight size={14} />
                    </NavLink>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 6: CITY EXPLORATION GALLERY */}
      <section className="editorial-section bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="section-eyebrow">POV: Saigon Golden Hour</span>
            <h2 className="section-title-large">Thành phố qua ống kính WanderHUB</h2>
            <p className="text-stone-600">Vẻ đẹp giao thoa giữa nét xưa cổ kính và nhịp sống trẻ trung, năng động.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                title: "Bưu Điện Trung Tâm",
                subtitle: "Ký ức thời gian",
                img: "/images/buu-dien.png"
              },
              {
                title: "Phố Đi Bộ Nguyễn Huệ",
                subtitle: "Trung tâm nhộn nhịp",
                img: "/images/nguyen-hue.png"
              },
              {
                title: "Công Viên Tao Đàn",
                subtitle: "Lá phổi xanh mát",
                img: "/images/tao-dan.png"
              },
              {
                title: "Nhà Thờ Đức Bà",
                subtitle: "Vẻ đẹp vượt năm tháng",
                img: "/images/ben-thanh.png"
              }
            ].map((pic, idx) => (
              <Reveal key={idx}>
                <div className="gallery-card">
                  <img src={pic.img} alt={pic.title} className="gallery-img" />
                  <div className="gallery-overlay-dark">
                    <span className="text-xs text-[#c96420] font-bold uppercase tracking-wider">{pic.subtitle}</span>
                    <h4 className="serif-h text-white text-xl mt-1">{pic.title}</h4>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 7: TESTIMONIALS */}
      <section className="editorial-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="section-eyebrow">Guest Stories</span>
            <h2 className="section-title-large">Đánh giá từ du khách đô thị</h2>
            <p className="text-stone-600">Những người đã thay đổi cách đi chơi nhờ sự đồng hành của AI và bản địa.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <Reveal>
              <div className="testimonial-card-editorial">
                <p className="testimonial-quote">
                  "Tôi đã sống ở Sài Gòn 5 năm nhưng chưa bao giờ biết tới một quán cafe nhỏ nằm trên lầu 3 của một căn chung cư cũ
                  đường Pasteur. AI của WanderHUB đã gợi ý cho tôi dựa trên mood thèm sự riêng tư. Thật đáng kinh ngạc!"
                </p>
                <div className="testimonial-author">Khánh Linh</div>
                <div className="testimonial-role">Creative Director, Quận 3</div>
              </div>
            </Reveal>
            <Reveal>
              <div className="testimonial-card-editorial">
                <p className="testimonial-quote">
                  "WanderHUB mang đến một trải nghiệm lịch lãm, tinh tế chuẩn boutique hotel. Cách tích hợp xe điện Xanh SM chạy thẳng
                  trong flow lịch trình giúp tôi đi chơi thảnh thơi mà không cần loay hoay đổi app."
                </p>
                <div className="testimonial-author">Anh Tuấn</div>
                <div className="testimonial-role">Kiến trúc sư, Quận 1</div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* SECTION 8: MOBILE APP PREVIEW */}
      <section className="editorial-section bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <Reveal>
              <span className="section-eyebrow">WanderHUB Pocket Guide</span>
              <h2 className="section-title-large">Mang theo người bạn đồng hành AI</h2>
              <p className="text-stone-600 leading-relaxed mb-6">
                Bản nâng cấp ứng dụng di động WanderHUB sắp tới sẽ mang toàn bộ tính năng re-route tự động, tích hợp thanh toán
                một chạm và định vị bản đồ thông minh vào lòng bàn tay của bạn.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-stone-100 bg-[#fdf8f3]">
                  <h4 className="font-bold text-[#1e4230]">Tải cho iOS</h4>
                  <p className="text-xs text-stone-500 mt-1">App Store · Sắp ra mắt</p>
                </div>
                <div className="p-4 rounded-xl border border-stone-100 bg-[#fdf8f3]">
                  <h4 className="font-bold text-[#1e4230]">Tải cho Android</h4>
                  <p className="text-xs text-stone-500 mt-1">Google Play · Sắp ra mắt</p>
                </div>
              </div>
            </Reveal>
            <Reveal>
              <div className="phone-mockup">
                <div className="phone-screen">
                  <div className="phone-header">
                    <span className="text-[10px] font-bold text-[#2d5a3d]">WanderHUB AI</span>
                    <span className="h-2 w-2 rounded-full bg-red-500" />
                  </div>
                  <div className="phone-screen-content flex flex-col gap-3 mt-3">
                    <div className="phone-card">
                      <span className="text-[10px] text-[#c96420] font-bold uppercase">Lịch trình tối nay</span>
                      <h4 className="font-bold text-[#1e4230] text-sm mt-1">Date Chill Sông Sài Gòn</h4>
                    </div>
                    <div className="flex flex-col gap-2">
                      {[
                        { step: "01", time: "18:00", title: "Cafe Trứng 3T - Ngô Văn Năm" },
                        { step: "02", time: "19:30", title: "Bến Bạch Đằng Waterbus" },
                        { step: "03", time: "20:45", title: "Rooftop Landmark 81 View" }
                      ].map((step, idx) => (
                        <div key={idx} className="phone-card flex gap-3 items-center">
                          <span className="h-6 w-6 rounded-full bg-[#2d5a3d]/10 text-[#2d5a3d] text-xs flex items-center justify-center p-1 font-bold">{step.step}</span>
                          <div>
                            <div className="text-[11px] font-bold text-[#1e4230]">{step.title}</div>
                            <div className="text-[9px] text-[#5a7a60]">{step.time}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* SECTION 9: PRICING PREVIEW */}
      <section className="editorial-section bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="section-eyebrow">Gói dịch vụ</span>
            <h2 className="section-title-large">Chọn gói phù hợp với bạn</h2>
            <p className="text-stone-600">Bắt đầu miễn phí, nâng cấp khi cần – không ràng buộc hợp đồng.</p>
          </div>
          <PricingGrid preview user={user} />
          <div className="text-center mt-10">
            <NavLink to="/pricing" className="btn btn-ghost inline-flex items-center gap-2">
              Xem chi tiết tất cả gói <ChevronRight size={16} />
            </NavLink>
          </div>
        </div>
      </section>

      {/* SECTION 10: CTA FINAL */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <Reveal className="max-w-6xl mx-auto text-center p-12 md:p-24 rounded-[3rem] bg-[#1e4230] shadow-2xl relative overflow-hidden">
          {/* Decorative background gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-[#2d5a3d]/40 to-transparent opacity-50 pointer-events-none"></div>
          
          <div className="relative z-10">
            <span className="text-[#c96420] font-bold tracking-[0.2em] uppercase text-sm mb-6 block">
              Start Your Discovery
            </span>
            <h2 className="serif-h text-4xl md:text-5xl text-white mb-6 leading-tight">
              Sẵn sàng để lên đường hôm nay?
            </h2>
            <p className="text-stone-300 text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
              Bắt đầu hành trình thiết lập lịch trình trải nghiệm đô thị Sài Gòn trọn vẹn chỉ với 3 giây chọn mood cùng WanderHUB.
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn bg-white text-[#1e4230] hover:bg-stone-100 border-none px-8 py-4 shadow-lg hover:shadow-xl transition-all font-bold">
                Lên lịch trình ngay <ArrowRight size={18} />
              </NavLink>
              <NavLink to="/explore" className="btn btn-glass text-white border-white/20 hover:bg-white/10 px-8 py-4 backdrop-blur-md">
                Khám phá địa điểm <Compass size={18} />
              </NavLink>
            </div>
          </div>
        </Reveal>
      </section>

    </motion.main>
  );
}

const PLAN_KEYS = { "Basic": "basic", "Premium": "premium", "International Tourist": "international" };

function PricingGrid({ preview = false, user = null, setUserPlan = null }) {
  const navigate = useNavigate();
  const [selecting, setSelecting] = useState(null);

  const handleSelectPlan = async (plan) => {
    if (!user) { navigate("/auth"); return; }
    const planKey = PLAN_KEYS[plan.name] || "basic";
    setSelecting(plan.name);
    try {
      const planData = await apiSelectPlan(plan.name, planKey);
      localStorage.setItem("wh_selected_plan", plan.name);
      localStorage.setItem("wh_plan_info", JSON.stringify(planData));
      if (setUserPlan) setUserPlan(planData);
      navigate("/planner");
    } catch {
      localStorage.setItem("wh_selected_plan", plan.name);
      navigate("/planner");
    } finally {
      setSelecting(null);
    }
  };

  return (
    <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-7xl mx-auto">
      {packages.map((plan) => (
        <Reveal key={plan.name} className={`price-card ${plan.highlight ? "featured" : ""}`}>
          <div className="flex items-center justify-between">
            <h3>{plan.name}</h3>
            {plan.highlight && <span className="badge">Best vibe</span>}
          </div>
          <div className="mt-4 text-2xl font-black text-[#1e4230]">{plan.price}</div>
          <p className="mt-3 text-sm leading-6 text-[#3d2b1a]/62">{plan.note}</p>
          <div className="mt-6 grid gap-2.5">
            {(preview ? plan.features.slice(0, 3) : plan.features).map((feature) => (
              <div key={feature} className="flex gap-3 text-sm text-[#3d2b1a]/75">
                <Check size={16} className="shrink-0 text-emerald-600 mt-0.5" /> {feature}
              </div>
            ))}
            {!preview && plan.notIncluded?.map((feature) => (
              <div key={feature} className="flex gap-3 text-sm text-stone-400 line-through">
                <X size={16} className="shrink-0 text-stone-300 mt-0.5" /> {feature}
              </div>
            ))}
          </div>
          <button
            onClick={() => handleSelectPlan(plan)}
            disabled={selecting === plan.name}
            className="btn btn-glass mt-7 w-full justify-center"
          >
            {selecting === plan.name
              ? "Đang xử lý..."
              : plan.price === "Miễn phí"
              ? "Dùng miễn phí"
              : plan.highlight
              ? "Bắt đầu Premium"
              : "Chọn gói này"}
          </button>
        </Reveal>
      ))}
    </div>
  );
}

function About() {
  return (
    <PageShell eyebrow="About WanderHUB" title="Wander + HUB = nền tảng kết nối trải nghiệm đô thị.">
      
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {cityStats.map((stat) => (
          <Reveal key={stat.value} className="text-center p-6 rounded-2xl bg-[#2d5a3d]/5 border border-[#2d5a3d]/10">
            <div className="text-3xl font-black text-[#1e4230]">{stat.value}</div>
            <div className="font-semibold text-[#2d5a3d] text-sm mt-1">{stat.label}</div>
            <div className="text-xs text-stone-500 mt-0.5">{stat.sub}</div>
          </Reveal>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] mb-16">
        <Reveal className="glass-panel">
          <h2>Câu chuyện thương hiệu</h2>
          <p>WanderHUB sinh ra từ một vấn đề rất đời: muốn đi chơi nhưng mất quá nhiều thời gian để tìm nơi, hỏi bạn bè, so sánh review, rồi tự đặt từng chặng xe.</p>
          <p>"Wander" là tinh thần lang thang khám phá. "HUB" là điểm kết nối giữa AI, trải nghiệm địa phương, đối tác vận chuyển và nhịp sống thành phố.</p>
          <p className="mt-3">Sản phẩm được xây dựng tại TP.HCM, lấy cảm hứng từ vị đắng ngot của ly cà phê sáng và nhịp sống không nghỉ của Sài Gòn.</p>
          
          <div className="mt-8 rounded-2xl overflow-hidden shadow-md h-[200px]">
            <img 
              src="/images/wanderhub-banner.png" 
              alt="WanderHUB Banner" 
              className="w-full h-full object-cover" 
            />
          </div>
        </Reveal>
        <div className="grid gap-5 content-start">
          {[
            [Compass, "Người bạn thổ địa thông minh", "WanderHUB không chỉ gợi ý địa điểm, mà hiểu bối cảnh đi chơi của bạn – thời tiết, ngân sách, tâm trạng."],
            [Bot, "AI + local experience", "AI xử lý sở thích cá nhân, còn dữ liệu địa phương tạo nên những gợi ý có chất riêng, không copy-paste từ Google Maps."],
            [BadgeCheck, "Premium nhưng thân thiện", "Thiết kế cho Gen Z đô thị: nhanh, đẹp, có gu và dùng được ngay – không cần hướng dẫn."],
            [Globe2, "Đà hướng quốc tế", "Hỗ trợ đa ngôn ngữ cho du khách nước ngoài khám phá TP.HCM theo phong cách địa phương nhất."],
          ].map(([Icon, title, text]) => (
            <Reveal key={title} className="mini-feature">
              <Icon className="text-cyan" />
              <div><h3>{title}</h3><p>{text}</p></div>
            </Reveal>
          ))}
        </div>
      </div>

      {/* Team Section */}
      <div className="mb-4">
        <h2 className="serif-h text-3xl text-[#1e4230] mb-2">Nhóm sáng lập</h2>
        <p className="text-stone-500 mb-8">Những người đang xây dựng tương lai đi lại thông minh tại TP.HCM.</p>
        <div className="grid md:grid-cols-3 gap-6">
          {teamMembers.map((member) => (
            <Reveal key={member.name} className="p-6 rounded-2xl border border-stone-100 bg-[#fdf8f3] text-center hover:shadow-lg transition">
              <img 
                src={member.avatar} 
                alt={member.name} 
                className="w-20 h-20 rounded-full object-cover mx-auto mb-4 ring-4 ring-[#2d5a3d]/10"
              />
              <h3 className="font-bold text-[#1e4230] text-lg">{member.name}</h3>
              <p className="text-sm text-[#c96420] font-semibold mt-1">{member.role}</p>
              <p className="text-sm text-stone-600 leading-relaxed mt-3">{member.bio}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </PageShell>
  );
}

function Pricing({ user, setUserPlan }) {
  return (
    <PageShell eyebrow="Service Packages / Pricing" title="Gói dịch vụ rõ ràng cho từng kiểu khám phá.">
      <PricingGrid user={user} setUserPlan={setUserPlan} />

      {/* Guarantee banner */}
      <Reveal className="mt-12 rounded-2xl bg-[#2d5a3d]/5 border border-[#2d5a3d]/10 p-8 flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
        <div className="h-14 w-14 rounded-full bg-[#2d5a3d] flex items-center justify-center shrink-0">
          <ShieldCheck size={28} className="text-white" />
        </div>
        <div>
          <h3 className="font-bold text-[#1e4230] text-xl">Bảo đảm hoàn tiền 7 ngày</h3>
          <p className="text-stone-600 text-sm mt-1 leading-relaxed">
            Nếu Premium không đáp ứng kỳ vọng, chúng tôi hoàn tiền đầy đủ trong vòng 7 ngày đầu sử dụng. Không cần giải thích.
          </p>
        </div>
        <NavLink to={!user ? "/auth" : hasPlan() ? "/planner" : "/pricing"} className="btn btn-primary shrink-0">Thử ngay</NavLink>
      </Reveal>

      {/* Inline FAQ */}
      <div className="mt-14">
        <h2 className="serif-h text-3xl text-[#1e4230] mb-6">Câu hỏi về giá được hỏi nhiều</h2>
        <div className="grid gap-4">
          {faqItems.slice(2).map((item) => (
            <Reveal key={item.q} className="faq-item bg-white border border-[#2d5a3d]/10 rounded-2xl p-6">
              <h3 className="font-bold text-[#1e4230] text-lg mb-2">{item.q}</h3>
              <p className="text-sm text-stone-600 leading-relaxed">{item.a}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </PageShell>
  );
}

function Explore() {
  const [selectedPost, setSelectedPost] = useState(null);

  return (
    <PageShell eyebrow="Explore / Blog / POV" title="POV thành phố theo vibe của bạn.">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {mockExploreDB.map((post) => (
          <Reveal key={post.id} className="blog-card bg-white border border-[#2d5a3d]/10 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition flex flex-col">
            <div className="blog-visual h-48 bg-stone-100" style={{ backgroundImage: `url(${post.image})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-[#1e4230] text-xl mb-2">{post.title}</h3>
                <p className="text-sm text-stone-600 leading-relaxed mb-4">{post.summary}</p>
              </div>
              <button 
                onClick={() => setSelectedPost(post)}
                className="text-link text-sm font-bold text-[#2d5a3d] hover:text-[#c96420] inline-flex items-center gap-1 transition mt-auto"
              >
                Đọc POV <ChevronRight size={16} />
              </button>
            </div>
          </Reveal>
        ))}
      </div>

      <AnimatePresence>
        {selectedPost && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-stone-900/60 backdrop-filter backdrop-blur-md"
          >
            <motion.div 
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              className="bg-[#fdf8f3] rounded-3xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-2xl relative"
            >
              <button 
                onClick={() => setSelectedPost(null)}
                className="absolute top-4 right-4 h-10 w-10 rounded-full bg-white/80 backdrop-filter backdrop-blur-sm hover:bg-white flex items-center justify-center text-stone-700 z-10 transition shadow-sm"
              >
                <X size={20} />
              </button>

              <div className="h-64 w-full bg-stone-200 relative">
                <img src={selectedPost.image} alt={selectedPost.title} className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#1e4230]/90 to-transparent flex items-end p-6">
                  <h2 className="serif-h text-white text-3xl font-bold">{selectedPost.title}</h2>
                </div>
              </div>

              <div className="p-6 sm:p-8">
                <div className="flex items-center justify-between text-xs text-stone-500 mb-6 border-b border-[#2d5a3d]/10 pb-4">
                  <span>Tác giả: <strong>{selectedPost.author}</strong></span>
                  <span>{selectedPost.readTime}</span>
                </div>
                <p className="text-stone-700 leading-relaxed text-base whitespace-pre-line">{selectedPost.content}</p>
                
                <div className="mt-8 flex gap-4">
                  <button 
                    onClick={() => setSelectedPost(null)} 
                    className="btn btn-primary"
                  >
                    Đóng bài viết
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageShell>
  );
}

function Contact() {
  const [formData, setFormData] = useState({ name: "", email: "", subject: "", message: "" });
  const [status, setStatus] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.email || !formData.message) {
      setStatus("Vui lòng điền đầy đủ Tên, Email và Nội dung tin nhắn.");
      return;
    }
    try {
      const result = await apiSubmitContact(formData.name, formData.email, formData.subject, formData.message);
      setStatus(result.message);
      setFormData({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      // Fallback to mock if backend unavailable
      setStatus("Gửi liên hệ thành công! Đội ngũ WanderHUB sẽ liên hệ lại qua email của bạn.");
      setFormData({ name: "", email: "", subject: "", message: "" });
    }
  };

  return (
    <PageShell eyebrow="Contact" title="Liên hệ WanderHUB.">
      <div className="grid gap-7 lg:grid-cols-[0.85fr_1.15fr]">
        <Reveal className="glass-panel">
          <div className="contact-row"><MapPin /> Thủ Đức, TP.HCM</div>
          <div className="contact-row"><Phone /> 1900-0905</div>
          <div className="contact-row"><Facebook /> WanderHUB</div>
          <div className="contact-row"><Instagram /> wanderhub.premium</div>
        </Reveal>
        <Reveal className="glass-panel">
          {status && (
            <div className={`p-4 rounded-xl mb-4 text-sm font-semibold ${status.includes("thành công") ? "bg-[#2d5a3d]/10 text-[#2d5a3d]" : "bg-red-500/10 text-red-700"}`}>
              {status}
            </div>
          )}
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <input 
              placeholder="Họ và tên" 
              value={formData.name} 
              onChange={(e) => setFormData({ ...formData, name: e.target.value })} 
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <input 
              placeholder="Email" 
              type="email" 
              value={formData.email} 
              onChange={(e) => setFormData({ ...formData, email: e.target.value })} 
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <input 
              placeholder="Chủ đề" 
              value={formData.subject} 
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })} 
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <textarea 
              placeholder="Bạn muốn trao đổi điều gì?" 
              rows="5" 
              value={formData.message} 
              onChange={(e) => setFormData({ ...formData, message: e.target.value })} 
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <button type="submit" className="btn btn-primary w-fit justify-center">Gửi liên hệ <Mail size={18} /></button>
          </form>
        </Reveal>
      </div>
    </PageShell>
  );
}

function FAQ() {
  return (
    <PageShell eyebrow="FAQ" title="Câu hỏi thường gặp.">
      <div className="grid gap-4">
        {faqItems.map((item) => (
          <Reveal key={item.q} className="faq-item bg-white border border-[#2d5a3d]/10 rounded-2xl p-6">
            <h3 className="font-bold text-[#1e4230] text-lg mb-2">{item.q}</h3>
            <p className="text-sm text-stone-600 leading-relaxed">{item.a}</p>
          </Reveal>
        ))}
      </div>
    </PageShell>
  );
}

function Terms() {
  const terms = [
    ["Data Privacy", "WanderHUB chỉ thu thập dữ liệu cần thiết để cá nhân hóa lịch trình, cải thiện gợi ý và hỗ trợ người dùng."],
    ["Third-party Liability", "Các dịch vụ từ bên thứ ba như vận chuyển, thanh toán hoặc điểm đến được vận hành theo chính sách của đối tác tương ứng."],
    ["Refund Policy", "Hoàn tiền được xem xét theo trạng thái sử dụng gói dịch vụ, lỗi hệ thống hoặc điều kiện riêng của từng hành trình."],
    ["Transport partner responsibility", "Giá xe, tài xế, thời gian đón và chất lượng chuyến đi thuộc trách nhiệm vận hành của đối tác vận chuyển."],
    ["User data protection", "Dữ liệu người dùng được bảo vệ bằng kiểm soát truy cập, mã hóa phù hợp và nguyên tắc tối thiểu hóa dữ liệu."],
  ];
  return (
    <PageShell eyebrow="Terms & Policies" title="Điều khoản minh bạch cho trải nghiệm đô thị an toàn.">
      <div className="grid gap-4">
        {terms.map(([title, text]) => (
          <Reveal key={title} className="policy-card bg-white border border-[#2d5a3d]/10 rounded-2xl p-6 flex gap-4">
            <ShieldCheck className="text-cyan shrink-0" />
            <div>
              <h3 className="font-bold text-[#1e4230] text-lg mb-1">{title}</h3>
              <p className="text-sm text-stone-600 leading-relaxed">{text}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </PageShell>
  );
}

function Auth({ setUser }) {
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [registerName, setRegisterName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [status, setStatus] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      setStatus("Vui lòng nhập đầy đủ Email và Mật khẩu.");
      return;
    }
    try {
      const data = await apiLogin(loginEmail, loginPassword);
      setUser(data.user);
      setStatus(`Đăng nhập thành công! Chào mừng ${data.user.name} quay lại.`);
      setTimeout(() => navigate("/"), 1200);
    } catch (err) {
      // Fallback to mock if backend unavailable
      if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
        const mockUser = { id: 0, name: loginEmail.split("@")[0], email: loginEmail };
        setUser(mockUser);
        setStatus(`Đăng nhập thành công (offline mode)! Chào mừng ${mockUser.name}.`);
        setTimeout(() => navigate("/"), 1200);
      } else {
        setStatus(err.message || "Đăng nhập thất bại.");
      }
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!registerName || !registerEmail || !registerPassword) {
      setStatus("Vui lòng điền đầy đủ thông tin để đăng ký.");
      return;
    }
    try {
      const data = await apiRegister(registerName, registerEmail, registerPassword);
      setStatus("Đăng ký tài khoản thành công! Bây giờ bạn có thể đăng nhập.");
      setLoginEmail(registerEmail);
      setRegisterName("");
      setRegisterEmail("");
      setRegisterPassword("");
    } catch (err) {
      if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
        setStatus("Đăng ký thành công (offline mode)! Bây giờ bạn có thể đăng nhập.");
        setLoginEmail(registerEmail);
        setRegisterName("");
        setRegisterEmail("");
        setRegisterPassword("");
      } else {
        setStatus(err.message || "Đăng ký thất bại.");
      }
    }
  };

  const handleGoogleLogin = () => {
    const mockUser = { id: 0, name: "GoogleUser", email: "google@wanderhub.com" };
    setUser(mockUser);
    setStatus("Đăng nhập bằng Google thành công!");
    setTimeout(() => {
      navigate("/");
    }, 1200);
  };

  return (
    <PageShell compact>
      <div className="mx-auto max-w-5xl mb-6">
        {status && (
          <div className={`p-4 rounded-xl text-center text-sm font-bold ${status.includes("thành công") ? "bg-[#2d5a3d]/10 text-[#2d5a3d]" : "bg-red-500/10 text-red-700"}`}>
            {status}
          </div>
        )}
      </div>
      <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-2">
        <Reveal className="auth-card bg-white border border-[#2d5a3d]/10 rounded-3xl p-8 flex flex-col gap-5">
          <h1 className="serif-h text-2xl text-[#1e4230]">Đăng nhập</h1>
          <p className="text-sm text-stone-500">Tiếp tục hành trình và quản lý các vibe đã lưu.</p>
          <form className="grid gap-4" onSubmit={handleLogin}>
            <input 
              id="auth-login-email" 
              placeholder="Email" 
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)} 
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <input 
              id="auth-login-password" 
              placeholder="Mật khẩu" 
              type="password" 
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <button type="submit" id="auth-btn-login" className="btn btn-primary w-full justify-center">Đăng nhập</button>
          </form>
          <button id="auth-btn-google" onClick={handleGoogleLogin} className="btn btn-glass w-full justify-center text-stone-700 hover:text-stone-900 border border-stone-200"><Globe2 size={18} /> Đăng nhập với Google</button>
        </Reveal>
        
        <Reveal className="auth-card bg-white border border-[#2d5a3d]/10 rounded-3xl p-8 flex flex-col gap-5">
          <h1 className="serif-h text-2xl text-[#1e4230]">Đăng ký</h1>
          <p className="text-sm text-stone-500">Tạo tài khoản để AI hiểu gu đi chơi của bạn hơn.</p>
          <form className="grid gap-4" onSubmit={handleRegister}>
            <input 
              id="auth-register-name" 
              placeholder="Tên của bạn" 
              value={registerName}
              onChange={(e) => setRegisterName(e.target.value)}
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <input 
              id="auth-register-email" 
              placeholder="Email" 
              value={registerEmail}
              onChange={(e) => setRegisterEmail(e.target.value)}
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <input 
              id="auth-register-password" 
              placeholder="Mật khẩu" 
              type="password" 
              value={registerPassword}
              onChange={(e) => setRegisterPassword(e.target.value)}
              className="border border-stone-200 rounded-xl p-3 bg-stone-50/50 w-full"
            />
            <button type="submit" id="auth-btn-register" className="btn btn-primary w-full justify-center">Tạo tài khoản</button>
          </form>
        </Reveal>
      </div>
    </PageShell>
  );
}

const HCM_FALLBACK_COORDS = [
  [10.7769, 106.7009],
  [10.7800, 106.7050],
  [10.7720, 106.6980],
  [10.7740, 106.7030],
  [10.7760, 106.7070],
];

function JourneyTracker({ rideLegs, transport, totalRideMinutes }) {
  const mapContainerRef = useRef(null);
  const leafletInstanceRef = useRef(null);
  const [activeIndex] = useState(0);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (leafletInstanceRef.current) {
      leafletInstanceRef.current.remove();
      leafletInstanceRef.current = null;
    }

    const getCoords = (leg, index) => {
      if (leg.latitude && leg.longitude) return [leg.latitude, leg.longitude];
      return HCM_FALLBACK_COORDS[index % HCM_FALLBACK_COORDS.length];
    };

    const coords = rideLegs.map((leg, i) => getCoords(leg, i));
    const center = coords[0] || [10.7769, 106.7009];

    const map = L.map(mapContainerRef.current, { zoomControl: true, scrollWheelZoom: false }).setView(center, 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
      maxZoom: 18,
    }).addTo(map);

    if (coords.length > 1) {
      L.polyline(coords, { color: "#2d5a3d", weight: 3, dashArray: "6 4", opacity: 0.8 }).addTo(map);
    }

    coords.forEach((coord, index) => {
      const isFirst = index === 0;
      const icon = L.divIcon({
        className: "",
        html: `<div style="
          width:28px;height:28px;border-radius:50%;
          background:${isFirst ? "#c96420" : "#2d5a3d"};
          color:#fff;display:flex;align-items:center;justify-content:center;
          font-size:12px;font-weight:900;
          box-shadow:0 2px 8px rgba(0,0,0,0.25);
          border:2px solid #fff;
        ">${index + 1}</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      L.marker(coord, { icon })
        .addTo(map)
        .bindPopup(`<b>${rideLegs[index].title}</b><br><small>${rideLegs[index].time || ""}</small>`);
    });

    if (coords.length > 1) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [40, 40] });
    }

    leafletInstanceRef.current = map;
    return () => {
      map.remove();
      leafletInstanceRef.current = null;
    };
  }, [rideLegs]);

  const isRide = transport === "Be / Xanh SM";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="journey-tracker-panel"
    >
      <div className="journey-tracker-inner">
        <div className="journey-tracker-map-wrap">
          <div ref={mapContainerRef} />
        </div>

        <div className="journey-tracker-timeline">
          <div className="journey-tracker-timeline-head">
            <strong>Theo dõi hành trình</strong>
            <small>{rideLegs.length} điểm · {totalRideMinutes} phút di chuyển</small>
          </div>

          {rideLegs.map((leg, index) => {
            const status = index === activeIndex ? "current" : index === activeIndex + 1 ? "next" : "waiting";
            return (
              <div key={`tracker-${leg.provider_id || leg.title}-${index}`} className="journey-tracker-leg">
                <div className={`journey-tracker-pin ${status === "current" ? "is-current" : status === "next" ? "is-next" : "is-waiting"}`}>
                  {index + 1}
                </div>
                <div className="journey-tracker-leg-info">
                  <b>{leg.title}</b>
                  <small>{leg.time || leg.rideLabel}{index > 0 && leg.travelFromPrevious ? ` · ${leg.travelFromPrevious} phút từ điểm trước` : ""}</small>
                </div>
                <span className={`journey-tracker-status ${status}`}>
                  {status === "current" ? "Đang đến" : status === "next" ? "Tiếp theo" : "Chờ"}
                </span>
              </div>
            );
          })}

          <div className="journey-tracker-booking">
            {isRide ? (
              <>
                <p className="journey-tracker-booking-note">
                  Ứng dụng sẽ nhận danh sách điểm dừng — copy tên điểm để nhập nhanh vào app.
                </p>
                <a
                  href="https://be.com.vn"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="journey-tracker-btn-be"
                >
                  <Car size={15} /> Mở Be
                </a>
                <a
                  href="https://xanhsm.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="journey-tracker-btn-xanh"
                >
                  <Car size={15} /> Mở Xanh SM
                </a>
              </>
            ) : (
              <div className="journey-tracker-walk-note">
                {transport === "Đi bộ thong thả"
                  ? "Bắt đầu đi bộ và theo dõi tiến độ từng điểm trên bản đồ."
                  : "Khởi động xe và theo dõi hành trình trên bản đồ."}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function hasPlan() {
  return !!localStorage.getItem("wh_selected_plan");
}

const FREE_MONTHLY_LIMIT = 2;

function getFreeUsageData() {
  try {
    const raw = localStorage.getItem("wh_free_usage");
    const currentMonth = new Date().toISOString().slice(0, 7);
    if (!raw) return { count: 0, month: currentMonth };
    const data = JSON.parse(raw);
    if (data.month !== currentMonth) return { count: 0, month: currentMonth };
    return data;
  } catch {
    return { count: 0, month: new Date().toISOString().slice(0, 7) };
  }
}

function PlannerV2({ userPlan = null, setUserPlan = null }) {
  const moodOptions = [
    { code: "chill", label: "Chill", hint: "Cafe, dạo phố, nhịp nhẹ", icon: Coffee },
    { code: "date", label: "Hẹn hò", hint: "Đẹp, riêng tư, ven sông", icon: Sparkles },
    { code: "group", label: "Đi nhóm", hint: "Rộng rãi, vui, dễ tụ tập", icon: Headphones },
    { code: "foodie", label: "Foodie", hint: "Ăn ngon, local, must-try", icon: Utensils },
    { code: "nightlife", label: "Nightlife", hint: "Bar, phố đêm, city lights", icon: Star },
    { code: "culture", label: "Văn hóa", hint: "Bảo tàng, phố cũ, nghệ thuật", icon: BadgeCheck },
    { code: "checkin", label: "Check-in", hint: "Ảnh đẹp, landmark, view", icon: Camera },
    { code: "hidden_gem", label: "Hidden gem", hint: "Ngóc ngách ít người biết", icon: Gem },
    { code: "healing", label: "Healing", hint: "Yên tĩnh, xanh, hồi phục", icon: Compass },
    { code: "premium", label: "Premium", hint: "Rooftop, fine dining, sang", icon: ShieldCheck },
    { code: "budget", label: "Tiết kiệm", hint: "Vừa túi tiền, nhiều giá trị", icon: Wallet },
    { code: "solo", label: "Solo", hint: "Tự do, dễ đi một mình", icon: Navigation },
  ];

  const districtOptions = [
    { name: "Quận 1", hint: "523 điểm", backend: "Quận 1" },
    { name: "Quận 2", hint: "Đang bổ sung", backend: "Thảo Điền", disabled: true },
    { name: "Quận 3", hint: "137 điểm", backend: "Quận 3" },
    { name: "Quận 4", hint: "23 điểm", backend: "Quận 4" },
    { name: "Quận 5", hint: "124 điểm", backend: "Quận 5" },
    { name: "Quận 10", hint: "43 điểm", backend: "Quận 10" },
    { name: "Bình Thạnh", hint: "7 điểm", backend: "Bình Thạnh" },
    { name: "Phú Nhuận", hint: "67 điểm", backend: "Phú Nhuận" },
  ];

  const budgetOptions = [
    { label: "Tiết kiệm", value: 200000, display: "150K - 200K" },
    { label: "Vừa đẹp", value: 500000, display: "300K - 500K" },
    { label: "Thoải mái", value: 800000, display: "500K - 800K" },
    { label: "Không giới hạn", value: 1200000, display: "Premium" },
  ];

  const timeOptions = [
    { label: "Sáng nhẹ", start: "08:30", end: "11:30", hint: "Cafe + check-in" },
    { label: "Trưa chiều", start: "13:30", end: "17:30", hint: "Indoor + văn hóa" },
    { label: "Sau giờ làm", start: "18:30", end: "22:00", hint: "Ăn tối + dạo phố" },
    { label: "Đêm Sài Gòn", start: "20:00", end: "23:30", hint: "Nightlife + ăn khuya" },
    { label: "Nửa ngày", start: "15:00", end: "22:00", hint: "4-5 điểm dừng" },
  ];

  const interestOptions = [
    { code: "checkin", label: "Chụp hình", icon: Camera },
    { code: "cafe_drink", label: "Uống cafe", icon: Coffee },
    { code: "food", label: "Trải nghiệm ẩm thực", icon: Utensils },
    { code: "culture", label: "Văn hóa", icon: BadgeCheck },
    { code: "nightlife", label: "Phố đêm", icon: Star },
    { code: "entertainment", label: "Hoạt động vui chơi", icon: Sparkles },
  ];

  const [vibe, setVibe] = useState("chill");
  const [budget, setBudget] = useState(budgetOptions[1]);
  const [timeSlot, setTimeSlot] = useState(timeOptions[2]);
  const [district, setDistrict] = useState(districtOptions[0]);
  const [interests, setInterests] = useState(["cafe_drink", "food", "checkin"]);
  const [transport, setTransport] = useState("Be / Xanh SM");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState("");
  const [showResult, setShowResult] = useState(true);
  const [aiResponse, setAiResponse] = useState(null);
  const [selectedProviderIds, setSelectedProviderIds] = useState(() => new Set());
  const [commercialSuggestions, setCommercialSuggestions] = useState([]);
  const [showRideBooking, setShowRideBooking] = useState(false);
  const trackedHoverRef = useRef(new Set());
  const didAutoGenerateRef = useRef(false);
  // Prefer server-side usage count when user is logged in (userPlan), fallback to localStorage
  const [freeUsageCount, setFreeUsageCount] = useState(() => {
    if (userPlan?.usage_this_month !== undefined) return userPlan.usage_this_month;
    return getFreeUsageData().count;
  });
  const isBasicPlan = !userPlan || userPlan.plan_key === "basic";
  const monthlyLimit = userPlan?.monthly_limit ?? FREE_MONTHLY_LIMIT;
  const limitReached = isBasicPlan && freeUsageCount >= monthlyLimit;
  const [routeCost, setRouteCost] = useState("552.500 VNĐ");
  const [routeDuration, setRouteDuration] = useState("4h 45m");
  const [routeStops, setRouteStops] = useState([
    {
      title: "Hana - Sinh Tố - Nước Ép",
      time: "18:30",
      desc: "Điểm mở đầu nhẹ nhàng cho mood chill, dễ ghép với cafe và ăn tối trong Quận 1.",
      category: "Quán uống / cafe",
      image_url: "https://commons.wikimedia.org/wiki/Special:FilePath/Coffee_in_Vietnam.jpg",
      score: 94,
      cost_estimated: 142500,
      avg_price_vnd: 142500,
      duration_min: 90,
      district: "Quận 1",
    },
    {
      title: "Nhà Hàng Royal Saigon",
      time: "20:00",
      desc: "Điểm ăn tối có điểm AI cao, phù hợp khi người dùng chọn trải nghiệm ẩm thực.",
      category: "Quán ăn / nhà hàng",
      image_url: "https://commons.wikimedia.org/wiki/Special:FilePath/Vietnamese_food.jpg",
      score: 92,
      cost_estimated: 185000,
      avg_price_vnd: 185000,
      duration_min: 105,
      district: "Quận 1",
    },
    {
      title: "Bui Vien Walking Street",
      time: "21:45",
      desc: "Kết thúc bằng phố đêm năng lượng cao, hợp với khung giờ sau giờ làm.",
      category: "Nightlife / bar",
      image_url: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Bui_Vien_Walking_Street_1.jpg/3840px-Bui_Vien_Walking_Street_1.jpg",
      score: 90,
      cost_estimated: 225000,
      avg_price_vnd: 225000,
      duration_min: 90,
      district: "Quận 1",
    },
    {
      title: "Nguyen Hue Walking Street",
      time: "19:10",
      desc: "Không gian đi bộ trung tâm, dễ chụp hình và nối tuyến sang cafe hoặc ăn tối.",
      category: "Check-in / tham quan",
      image_url: "/images/nguyen-hue.jpg",
      score: 89,
      cost_estimated: 80000,
      avg_price_vnd: 80000,
      duration_min: 45,
      district: "Quận 1",
    },
    {
      title: "Secret Garden Rooftop",
      time: "20:20",
      desc: "Rooftop có không khí riêng tư, hợp hẹn hò hoặc nhóm nhỏ muốn ăn tối nhẹ.",
      category: "Quán ăn / nhà hàng",
      image_url: "/images/secret-garden.png",
      score: 91,
      cost_estimated: 220000,
      avg_price_vnd: 220000,
      duration_min: 90,
      district: "Quận 1",
    },
    {
      title: "Bến Thành Market",
      time: "21:20",
      desc: "Điểm kết route dễ nhận diện, có nhiều lựa chọn ăn vặt và mua sắm nhanh.",
      category: "Check-in / tham quan",
      image_url: "/images/ben-thanh.jpg",
      score: 87,
      cost_estimated: 100000,
      avg_price_vnd: 100000,
      duration_min: 50,
      district: "Quận 1",
    },
  ]);

  const selectedMood = moodOptions.find((item) => item.code === vibe) || moodOptions[0];
  const selectedInterests = interests
    .map((code) => interestOptions.find((item) => item.code === code)?.label)
    .filter(Boolean)
    .join(", ");

  const fallbackImageForStop = (item) => {
    const categoryCode = item?.category_code || "";
    const categoryText = (item?.category || "").toLowerCase();
    if (categoryCode === "food" || categoryText.includes("ăn") || categoryText.includes("nhà hàng")) return "/images/oc-dao.png";
    if (categoryCode === "cafe_drink" || categoryText.includes("cafe") || categoryText.includes("uống")) return "/images/secret-garden.png";
    if (categoryCode === "nightlife" || categoryText.includes("nightlife")) return "/images/nguyen-hue.jpg";
    if (categoryCode === "culture" || categoryText.includes("văn hóa")) return "/images/war-museum.jpg";
    if (categoryCode === "entertainment" || categoryText.includes("vui chơi")) return "/images/landmark-81.jpg";
    return "/images/ben-thanh.jpg";
  };

  const mapStops = (stops) => stops.map((stop) => ({
    provider_id: stop.provider_id,
    title: stop.title,
    time: stop.arrival_time,
    desc: stop.description || stop.reason,
    reason: stop.reason,
    category: stop.category,
    category_code: stop.category_code,
    image_url: stop.image_url,
    score: stop.score || stop.ai_score || Math.round(84 + Math.random() * 10),
    cost_estimated: stop.cost_estimated,
    avg_price_vnd: stop.avg_price_vnd || stop.cost_estimated,
    duration_min: stop.duration_min,
    district: stop.district,
    price_min_vnd: stop.price_min_vnd,
    price_max_vnd: stop.price_max_vnd,
    latitude: stop.latitude,
    longitude: stop.longitude,
    business_tag: stop.business_tag,
  }));

  const trackStopInteraction = async (item, eventType, metadata = {}) => {
    if (!aiResponse?.session_id && eventType !== "reroute") return;
    if (!item?.provider_id && !["view", "reroute"].includes(eventType)) return;

    if (eventType === "hover") {
      const hoverKey = `${aiResponse.session_id}-${item.provider_id}`;
      if (trackedHoverRef.current.has(hoverKey)) return;
      trackedHoverRef.current.add(hoverKey);
    }

    try {
      await apiTrackInteraction({
        session_id: aiResponse?.session_id,
        itinerary_id: aiResponse?.itinerary_id,
        provider_id: item?.provider_id,
        event_type: eventType,
        metadata: {
          title: item?.title,
          category: item?.category_code || item?.category,
          mood: vibe,
          district: district.backend,
          ...metadata,
        },
      });
    } catch (err) {
      console.warn("[Planner] Interaction tracking skipped:", err.message);
    }
  };

  const isStopSelected = (item) => selectedProviderIds.has(item.provider_id || item.title);

  const toggleStopSelection = (item, index) => {
    const selectionKey = item.provider_id || item.title;
    const nextSelected = !selectedProviderIds.has(selectionKey);
    setSelectedProviderIds((prev) => {
      const next = new Set(prev);
      if (nextSelected) next.add(selectionKey);
      else next.delete(selectionKey);
      return next;
    });
    trackStopInteraction(item, nextSelected ? "choose" : "dislike", { step: index + 1 });
  };

  const selectedStops = routeStops.filter((item) => isStopSelected(item));
  const rideStops = selectedStops.slice(0, 3);
  const rideLegs = useMemo(() => {
    const estimateMinutes = (from, to) => {
      if (!from?.latitude || !from?.longitude || !to?.latitude || !to?.longitude) return 12;
      const toRad = (value) => (value * Math.PI) / 180;
      const earthKm = 6371;
      const dLat = toRad(to.latitude - from.latitude);
      const dLon = toRad(to.longitude - from.longitude);
      const a = Math.sin(dLat / 2) ** 2
        + Math.cos(toRad(from.latitude)) * Math.cos(toRad(to.latitude)) * Math.sin(dLon / 2) ** 2;
      const distance = earthKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      return Math.max(6, Math.round((distance / 18) * 60 + 5));
    };
    return rideStops.map((stop, index) => ({
      ...stop,
      travelFromPrevious: index === 0 ? 0 : estimateMinutes(rideStops[index - 1], stop),
      rideLabel: index === 0 ? "Điểm đón" : `Chặng ${index}`,
    }));
  }, [rideStops]);
  const totalRideMinutes = rideLegs.reduce((sum, stop) => sum + stop.travelFromPrevious, 0);

  const handleGenerate = async (isAutoGenerate = false) => {
    if (!isAutoGenerate && limitReached) return;

    setIsGenerating(true);
    setShowResult(false);
    const steps = [
      "Layer 1: đọc mood, khu vực, thời gian và sở thích đã chọn...",
      "Layer 2: áp business rules theo ngân sách, buổi đi và độ gần nhau...",
      "Layer 3: chấm điểm provider theo SQUAD, mood match và diversity...",
      "Hoàn tất! Đang dựng route cá nhân hóa...",
    ];

    let currentStepIdx = 0;
    setGenerationStep(steps[0]);
    const stepInterval = setInterval(() => {
      currentStepIdx += 1;
      if (currentStepIdx < steps.length) setGenerationStep(steps[currentStepIdx]);
    }, 600);

    try {
      const result = await apiGenerateItinerary({
        mood: vibe,
        budget_max: budget.value,
        time_start: timeSlot.start,
        time_end: timeSlot.end,
        district: district.backend,
        food_preference: selectedInterests,
        transport,
        is_auto_generate: isAutoGenerate,
        max_stops: timeSlot.label === "Nửa ngày" ? 8 : 6,
      });

      clearInterval(stepInterval);
      setAiResponse(result);
      setSelectedProviderIds(new Set());
      setCommercialSuggestions(mapStops(result.commercial_suggestions || []));
      setShowRideBooking(false);
      trackedHoverRef.current.clear();
      setRouteStops(mapStops(result.stops));
      setRouteCost(result.total_cost);
      setRouteDuration(result.total_duration);
      apiTrackInteraction({
        session_id: result.session_id,
        itinerary_id: result.itinerary_id,
        event_type: "view",
        metadata: {
          mood: vibe,
          district: district.backend,
          result_count: result.stops?.length || 0,
        },
      }).catch((err) => console.warn("[Planner] View tracking skipped:", err.message));
      setIsGenerating(false);
      setShowResult(true);
      if (!isAutoGenerate) {
        const usage = getFreeUsageData();
        const newCount = usage.count + 1;
        localStorage.setItem("wh_free_usage", JSON.stringify({ count: newCount, month: usage.month }));
        setFreeUsageCount(newCount);
        // Sync usage count from server for accuracy
        apiGetMyPlan().then((plan) => {
          setFreeUsageCount(plan.usage_this_month);
          if (setUserPlan) setUserPlan(plan);
          localStorage.setItem("wh_plan_info", JSON.stringify(plan));
        }).catch(() => {});
      }
    } catch (err) {
      clearInterval(stepInterval);
      console.warn("[Planner] Backend unavailable, using fallback:", err.message);
      setCommercialSuggestions([
        {
          title: "Hidden gem mới: Workshop cuối tuần",
          time: "Pick later",
          desc: "Điểm đề xuất thêm cho khách muốn trải nghiệm dịch vụ mới sau tuyến chính.",
          category: "Partner discovery",
          image_url: "/images/secret-garden.png",
          score: 88,
          cost_estimated: 180000,
          avg_price_vnd: 180000,
          duration_min: 75,
          district: district.name,
          business_tag: "partner_seed",
        },
      ]);
      setShowRideBooking(false);
      setRouteStops([
        { title: `${selectedMood.label} starter - ${district.name}`, time: timeSlot.start, desc: `Điểm mở đầu tối ưu cho ${selectedMood.hint} và sở thích ${selectedInterests}.`, category: "AI matched", score: 86, district: district.name },
        { title: `${selectedInterests.split(",")[0] || "Trải nghiệm"} nổi bật`, time: "19:45", desc: "AI ưu tiên điểm có chi phí vừa ngân sách, cùng khu vực và không lặp category liền kề.", category: "Personalized", score: 84, district: district.name },
        { title: `Điểm kết route tại ${district.name}`, time: timeSlot.end, desc: "Chọn điểm kết phù hợp khung giờ để khách ít phải di chuyển ngược tuyến.", category: "Route ending", score: 82, district: district.name },
      ]);
      setRouteCost(budget.display);
      setRouteDuration(timeSlot.hint);
      setIsGenerating(false);
      setShowResult(true);
      if (!isAutoGenerate) {
        const usage = getFreeUsageData();
        const newCount = usage.count + 1;
        localStorage.setItem("wh_free_usage", JSON.stringify({ count: newCount, month: usage.month }));
        setFreeUsageCount(newCount);
      }
    }
  };

  const navigate = useNavigate();
  useEffect(() => {
    if (!localStorage.getItem("wh_selected_plan")) {
      navigate("/pricing", { replace: true });
      return;
    }
    if (didAutoGenerateRef.current) return;
    didAutoGenerateRef.current = true;
    const timer = window.setTimeout(() => {
      handleGenerate(true);
    }, 250);
    return () => window.clearTimeout(timer);
  }, []);

  const reroute = async () => {
    if (aiResponse?.stops?.length) {
      const replaceStep = Math.floor(Math.random() * aiResponse.stops.length) + 1;
      trackStopInteraction(null, "reroute", { replace_step: replaceStep });
      try {
        const result = await apiRerouteItinerary({
          itinerary_id: aiResponse.itinerary_id,
          stops: aiResponse.stops,
          replace_step: replaceStep,
          mood: vibe,
          budget_max: budget.value,
          district: district.backend,
        });
        const nextResponse = { ...result, session_id: result.session_id || aiResponse.session_id };
        setAiResponse(nextResponse);
        setSelectedProviderIds(new Set());
        setCommercialSuggestions(mapStops(nextResponse.commercial_suggestions || commercialSuggestions));
        setShowRideBooking(false);
        setRouteStops(mapStops(nextResponse.stops));
        setRouteCost(nextResponse.total_cost);
        setRouteDuration(nextResponse.total_duration);
      } catch {
        setRouteStops((prev) => [...prev.slice(1), prev[0]]);
      }
    } else {
      setRouteStops((prev) => [...prev.slice(1), prev[0]]);
    }
  };

  return (
    <PageShell eyebrow="AI Trip Planner" title="Tạo lịch trình đi chơi theo mood trong vài giây.">
      <div className="grid gap-7 lg:grid-cols-[0.9fr_1.1fr]">
        <Reveal className="planner-panel planner-control-panel">
          <div className="planner-field">
            <div className="planner-field-head">
              <span>Mood / Vibe</span>
              <small>Theo bảng moods trong database</small>
            </div>
            <div className="choice-grid mood-choice-grid">
              {moodOptions.map(({ code, label, hint, icon: Icon }) => (
                <button key={code} type="button" className={`choice-card ${vibe === code ? "is-active" : ""}`} onClick={() => setVibe(code)}>
                  <Icon size={17} />
                  <strong>{label}</strong>
                  <small>{hint}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="planner-field">
            <div className="planner-field-head">
              <span>Khu vực Sài Gòn</span>
              <small>Chạm để chọn quận, không cần gõ</small>
            </div>
            <div className="district-grid">
              {districtOptions.map((item) => (
                <button key={item.name} type="button" disabled={item.disabled} className={`district-chip ${district.name === item.name ? "is-active" : ""} ${item.disabled ? "is-disabled" : ""}`} onClick={() => setDistrict(item)}>
                  <strong>{item.name}</strong>
                  <small>{item.hint}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="planner-two-col">
            <div className="planner-field">
              <div className="planner-field-head"><span>Ngân sách</span></div>
              <div className="segmented-stack">
                {budgetOptions.map((item) => (
                  <button key={item.label} type="button" className={`segment-btn ${budget.label === item.label ? "is-active" : ""}`} onClick={() => setBudget(item)}>
                    <span>{item.label}</span>
                    <small>{item.display}</small>
                  </button>
                ))}
              </div>
            </div>

            <div className="planner-field">
              <div className="planner-field-head"><span>Thời gian tối ưu</span></div>
              <div className="segmented-stack">
                {timeOptions.map((item) => (
                  <button key={item.label} type="button" className={`segment-btn ${timeSlot.label === item.label ? "is-active" : ""}`} onClick={() => setTimeSlot(item)}>
                    <span>{item.label}</span>
                    <small>{item.start} - {item.end} · {item.hint}</small>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="planner-field">
            <div className="planner-field-head">
              <span>Mình muốn ưu tiên</span>
              <small>Checkbox chọn nhiều mục để cá nhân hóa route</small>
            </div>
            <div className="interest-grid">
              {interestOptions.map(({ code, label, icon: Icon }) => {
                const active = interests.includes(code);
                return (
                  <button key={code} type="button" className={`interest-chip ${active ? "is-active" : ""}`} onClick={() => setInterests((prev) => active ? prev.filter((item) => item !== code) : [...prev, code])}>
                    <span className="interest-check">{active ? <Check size={13} /> : null}</span>
                    <Icon size={16} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="planner-field">
            <div className="planner-field-head"><span>Phương tiện di chuyển</span></div>
            <div className="transport-row">
              {["Be / Xanh SM", "Đi bộ thong thả", "Tự lái xe máy"].map((item) => (
                <button key={item} type="button" className={`transport-chip ${transport === item ? "is-active" : ""}`} onClick={() => setTransport(item)}>
                  <Car size={16} /> {item}
                </button>
              ))}
            </div>
          </div>

          <button id="planner-btn-submit" onClick={() => handleGenerate(false)} disabled={isGenerating || limitReached} className="btn btn-primary w-full justify-center mt-2">
            {isGenerating ? "Đang xử lý..." : "Lên lịch trình AI"} <Sparkles size={18} />
          </button>
          {isBasicPlan && !limitReached && (
            <p className="text-xs text-center text-stone-400 mt-2">
              Gói <strong>Basic</strong>: còn <strong>{monthlyLimit - freeUsageCount}</strong>/{monthlyLimit} lượt tạo miễn phí tháng này
            </p>
          )}
          {!isBasicPlan && (
            <p className="text-xs text-center text-stone-400 mt-2">
              Gói <strong>{userPlan?.plan_name}</strong>: tạo lịch trình không giới hạn
            </p>
          )}
          {limitReached && (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-center text-sm">
              <p className="font-semibold text-amber-700">Đã dùng hết {monthlyLimit} lượt miễn phí tháng này.</p>
              <p className="text-amber-600 mt-1">Nâng cấp Premium để tạo lịch trình không giới hạn.</p>
              <NavLink to="/pricing" className="btn btn-primary mt-3 w-full justify-center text-sm">
                Xem gói Premium <ChevronRight size={14} />
              </NavLink>
            </div>
          )}
        </Reveal>

        <Reveal className="planner-output">
          {isGenerating ? (
            <div className="flex flex-col items-center justify-center min-h-[350px] gap-6 text-center">
              <div className="w-12 h-12 border-4 border-[#2d5a3d] border-t-transparent rounded-full animate-spin"></div>
              <div>
                <h4 className="font-bold text-[#1e4230] text-lg">Đang tính toán...</h4>
                <p className="text-sm text-stone-500 mt-2">{generationStep}</p>
              </div>
            </div>
          ) : showResult ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="serif-h text-2xl text-[#1e4230]">Tuyến đường AI khuyên dùng</h2>
                  <p className="planner-result-context">{selectedMood.label} · {district.name} · {selectedInterests}</p>
                </div>
                <button id="planner-btn-reroute" onClick={reroute} className="icon-btn" aria-label="Re-route"><RefreshCcw size={18} /></button>
              </div>
              <div className="route-summary flex gap-2">
                <span className="flex items-center gap-1"><Wallet size={16} /> {routeCost}</span>
                <span className="flex items-center gap-1"><Clock3 size={16} /> {routeDuration}</span>
                <span className="flex items-center gap-1"><Car size={16} /> {transport}</span>
              </div>
              <div className="itinerary-card-grid">
                {routeStops.map((item, index) => (
                  <motion.div
                    layout
                    key={`${item.provider_id || item.title}-${index}`}
                    className={`recommendation-card ${isStopSelected(item) ? "is-selected" : ""}`}
                    onMouseEnter={() => trackStopInteraction(item, "hover", { step: index + 1 })}
                    onClick={() => trackStopInteraction(item, "click", { step: index + 1 })}
                  >
                    <div className="recommendation-image-wrap">
                      <img
                        src={item.image_url || fallbackImageForStop(item)}
                        alt={item.title}
                        onError={(event) => {
                          event.currentTarget.onerror = null;
                          event.currentTarget.src = fallbackImageForStop(item);
                        }}
                      />
                      <span className="recommendation-step">{String(index + 1).padStart(2, "0")}</span>
                    </div>
                    <div className="recommendation-body">
                      <div className="recommendation-card-head">
                        <b>{item.title}</b>
                        <span>{item.time}</span>
                      </div>
                      <p>{item.desc}</p>
                      <div className="place-meta-row">
                        <small>{item.category || "AI pick"}</small>
                        <small>{item.district || district.name}</small>
                      </div>
                      <div className="recommendation-metrics">
                        <span><Wallet size={14} /> Giá TB {Number(item.avg_price_vnd || item.cost_estimated || 0).toLocaleString("vi-VN")} VNĐ</span>
                        {item.duration_min ? <span><Clock3 size={14} /> {item.duration_min} phút</span> : null}
                        <span><Sparkles size={14} /> {Math.round(item.score || 88)}/100</span>
                      </div>
                      <small className="recommendation-reason">{item.reason || "Đề xuất vì khớp mood, cùng khu vực ưu tiên và giúp route ít lặp trải nghiệm."}</small>
                      <button
                        type="button"
                        className={`recommendation-check-row ${isStopSelected(item) ? "is-checked" : ""}`}
                        aria-pressed={isStopSelected(item)}
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleStopSelection(item, index);
                        }}
                      >
                        <span className="recommendation-checkbox">{isStopSelected(item) ? <Check size={14} /> : null}</span>
                        <span>{isStopSelected(item) ? "Đã thêm vào hành trình" : "Chọn điểm này"}</span>
                      </button>
                    </div>
                  </motion.div>
                ))}
                {commercialSuggestions.length ? (
                  <div className="commercial-suggestion-panel">
                    <div className="commercial-suggestion-head">
                      <div>
                        <strong>✨ Ngoài ra, có thể bạn quan tâm</strong>
                        <small>Được đề xuất từ đối tác mới — không nằm trong tuyến AI chính.</small>
                      </div>
                      <span>Đối tác</span>
                    </div>
                    <div className="commercial-suggestion-grid">
                      {commercialSuggestions.map((item, index) => (
                        <button
                          key={`${item.provider_id || item.title}-partner-${index}`}
                          type="button"
                          className={`commercial-suggestion-card ${isStopSelected(item) ? "is-selected" : ""}`}
                          onClick={() => toggleStopSelection(item, routeStops.length + index)}
                        >
                          <img
                            src={item.image_url || fallbackImageForStop(item)}
                            alt={item.title}
                            onError={(event) => {
                              event.currentTarget.onerror = null;
                              event.currentTarget.src = fallbackImageForStop(item);
                            }}
                          />
                          <span>
                            <b>{item.title}</b>
                            <small>{item.category || "Hidden gem"} · {Number(item.avg_price_vnd || item.cost_estimated || 0).toLocaleString("vi-VN")} VNĐ</small>
                          </span>
                          <i>{isStopSelected(item) ? "Đã chọn" : "Thêm"}</i>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
                <div className="booking-next-panel">
                  <div>
                    <strong>{selectedStops.length ? `Đã chọn ${selectedStops.length} điểm` : "Chưa chọn điểm nào"}</strong>
                    <small>{selectedStops.length ? selectedStops.map((item) => item.title).slice(0, 3).join(" · ") : "Tick vào checkbox trên card để đi tiếp sang đặt xe."}</small>
                  </div>
                  <button
                    type="button"
                    disabled={!selectedStops.length}
                    className="booking-next-btn"
                    onClick={() => {
                      selectedStops.forEach((item, index) => trackStopInteraction(item, "save", { step: index + 1, next_stage: "ride_booking" }));
                      setShowRideBooking(true);
                    }}
                  >
                    <Car size={16} /> Tiếp tục đặt xe
                  </button>
                </div>
                {showRideBooking && rideLegs.length > 0 ? (
                  <JourneyTracker
                    rideLegs={rideLegs}
                    transport={transport}
                    totalRideMinutes={totalRideMinutes}
                  />
                ) : null}
              </div>
            </motion.div>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[350px] text-center text-stone-400">
              <Compass size={48} className="stroke-1 mb-4" />
              <p>Chọn vài hộp bên trái rồi bấm nút để bắt đầu thiết kế hành trình.</p>
            </div>
          )}
        </Reveal>
      </div>
    </PageShell>
  );
}

function App() {
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [userPlan, setUserPlan] = useState(null);

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem("wanderhub_token");
    if (!token) return;
    apiGetMe()
      .then((profile) => setUser(profile))
      .catch(() => clearToken());
  }, []);

  // Sync plan from server whenever user logs in / out
  useEffect(() => {
    if (!user) {
      setUserPlan(null);
      return;
    }
    apiGetMyPlan()
      .then((plan) => {
        setUserPlan(plan);
        localStorage.setItem("wh_selected_plan", plan.plan_name);
        localStorage.setItem("wh_plan_info", JSON.stringify(plan));
      })
      .catch(() => {
        // User has no plan on server yet — keep whatever is in localStorage
      });
  }, [user]);

  const handleLogout = () => {
    setUser(null);
    setUserPlan(null);
    localStorage.removeItem("wh_selected_plan");
    localStorage.removeItem("wh_plan_info");
    clearToken();
  };

  return (
    <>
      <Navbar user={user} userPlan={userPlan} onLogout={handleLogout} />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Home user={user} />} />
          <Route path="/about" element={<About />} />
          <Route path="/pricing" element={<Pricing user={user} setUserPlan={setUserPlan} />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/auth" element={<Auth setUser={setUser} />} />
          <Route path="/planner" element={<PlannerV2 userPlan={userPlan} setUserPlan={setUserPlan} />} />
        </Routes>
      </AnimatePresence>
      <Footer user={user} />
      <FloatingChatBot />
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
