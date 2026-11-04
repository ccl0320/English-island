# 雲端存檔（帳號密碼登入）設定

遊戲標題畫面有「☁️ Log in to save」按鈕。孩子用「帳號名稱 + 密碼」登入後，進度會存到雲端，換手機、平板或電腦登入同一個帳號就能接著玩。不需要 email。

還沒設定前，遊戲照常運作，進度只存在這台裝置。

## 一次性設定（約 10 分鐘，免費）

1. 到 https://console.firebase.google.com 用 Google 帳號登入，按「新增專案」，名稱例如 `english-island`（Google Analytics 可以關掉）。
2. 左側「建構 → Authentication → 開始使用 → 登入方式」，啟用 **電子郵件/密碼**（只開第一個開關即可）。
3. 左側「建構 → Firestore Database → 建立資料庫」，選離你近的地區（例如 `asia-east1` 台灣），用「正式版模式」建立。
4. 在 Firestore 的「規則」分頁，整段換成下面這段後按「發布」（每個孩子只能讀寫自己的存檔）：

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /saves/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
  }
}
```

5. 專案總覽旁的齒輪「專案設定 → 一般 → 你的應用程式」，按 `</>`（網頁）新增一個應用程式，複製畫面上 `firebaseConfig` 裡的 `apiKey` 和 `projectId`。
6. 打開 `index.html`，搜尋 `const CLOUD=`，填入：

```js
const CLOUD={apiKey:'AIza...你的apiKey',projectId:'english-island-xxxx'};
```

推上 main 後，網頁版和自動產生的 APK 都會有登入功能。

> apiKey 放在網頁裡是正常的（Firebase 的網頁金鑰本來就是公開的），安全性靠第 4 步的規則保護。若要限制金鑰，請同時允許 `ccl0320.github.io` 和 `appassets.androidplatform.net`（APK 用）。

## 運作方式

- 登入時，這台裝置原有的進度會自動搬進帳號。如果帳號和裝置上各有不同進度，會讓孩子選要保留哪一個。
- 之後每次存檔約 2 秒後自動上傳；離線時先存在裝置，連上網路後自動補傳。
- 開遊戲時會自動抓雲端較新的進度。
- 登出會清除這台裝置上的進度（雲端仍保留），適合教室共用平板。
- 帳號名稱在系統裡會變成 `名稱@players.english-island.app`（不會寄信）。忘記密碼時：Firebase →  Authentication → 使用者，找到該帳號 → 「重設密碼」無法寄信，請改用「刪除帳號」後重建，或在選單裡直接編輯密碼。
