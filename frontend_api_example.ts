// API 調用範例 - 配合前端使用

// 創建新用戶（使用 TownPass ID）
export const createUser = async (petName: string, townpassId: string) => {
  const response = await fetch(`${API_BASE_URL}/users/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: townpassId,  // 從 TownPass 來的唯一 ID
      pet_name: petName,     // 寵物名稱
    }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to create user');
  }
  
  return response.json();
};

// 前端使用範例
const handleCreateUser = async () => {
  try {
    const townpassId = townpassUser?.id;
    
    if (!townpassId) {
      // 如果沒有 TownPass ID，使用預設帳號 id="1"
      setUserId("1");
      navigate("/");
    } else {
      // 有 TownPass ID，創建/獲取用戶
      const user = await createUser(petName.trim(), townpassId);
      setUserId(user.id);  // user.id 會是 townpassId
      navigate("/");
    }
  } catch (error) {
    console.error(error);
  }
};

// 後續所有 API 調用都使用 userId (字串型)
// GET  /users/{userId}/pet
// POST /users/{userId}/exercise
// POST /users/{userId}/daily-check
// etc.
