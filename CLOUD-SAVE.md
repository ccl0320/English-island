# 雲端存檔（帳號密碼登入）設定 · Supabase

遊戲標題畫面有「☁️ Log in to save」按鈕。孩子用「帳號名稱 + 密碼」登入後，進度會存到雲端，換手機、平板或電腦登入同一個帳號就能接著玩。不需要 email。

還沒設定前，遊戲照常運作，進度只存在這台裝置。

## 一次性設定（約 10 分鐘，免費）

1. 到 https://supabase.com 註冊（可用 GitHub 帳號登入），按 **New project**。名稱例如 `english-island`，資料庫密碼隨便設一個強密碼並記下來，Region 選 **Northeast Asia (Tokyo)** 或 **Southeast Asia (Singapore)**。
2. **關掉 email 驗證（很重要）**：左側 **Authentication → Sign In / Providers**（舊版介面在 Providers → Email），
   - 確認 **Email** 是開啟的，
   - 把 **Confirm email** 關掉，按 Save。
   - 同頁的 **Allow new users to sign up** 要保持開啟。
   （因為孩子的帳號沒有真的 email，不關掉的話建帳號會卡住。）
3. 左側 **SQL Editor → New query**，貼上下面整段，按 **Run**：

```sql
create table public.saves (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  username   text,
  data       jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.saves enable row level security;

create policy "own save: read"   on public.saves for select using (auth.uid() = user_id);
create policy "own save: insert" on public.saves for insert with check (auth.uid() = user_id);
create policy "own save: update" on public.saves for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

   這會建立存檔表，並設定每個孩子只能讀寫自己的存檔。
4. 左側齒輪 **Project Settings → API**（新版叫 **Data API** 和 **API Keys**），複製：
   - **Project URL**（像 `https://abcdxyz.supabase.co`）
   - **anon public** key（新版叫 **Publishable key**，`sb_publishable_` 開頭）。**不要**用 `service_role` / secret key。
5. 把這兩個值貼給 Claude，或自己打開 `index.html`，搜尋 `const CLOUD=`，填入：

```js
const CLOUD={url:'https://abcdxyz.supabase.co',key:'sb_publishable_...或 eyJ... 的 anon key'};
```

推上 main 後，網頁版和自動產生的 APK 都會有登入功能。

> anon / publishable key 放在網頁裡是正常的，本來就是公開用的；資料安全靠第 3 步的 row level security 規則。

## 運作方式

- 登入時，這台裝置原有的進度會自動搬進帳號。如果帳號和裝置上各有不同進度，會讓孩子選要保留哪一個。
- 之後每次存檔約 2 秒後自動上傳；離線時先存在裝置，連上網路後自動補傳。
- 開遊戲時會自動抓雲端較新的進度。
- 登出會清除這台裝置上的進度（雲端仍保留），適合教室共用平板。
- 在 Supabase 的 **Table Editor → saves** 可以看到每個孩子的帳號名稱和進度。

## 要注意

- 帳號名稱在系統裡會變成 `名稱@players.english-island.app`（不會寄信，所以沒有「忘記密碼」信件）。
- 忘記密碼時：到 **Authentication → Users**，找到該帳號，刪除後用同一個名稱和新密碼重建，再在還留有進度的那台裝置上登入，進度就會搬進去。
- 免費方案的專案如果**連續 7 天沒有人使用**會被暫停，需要到 Supabase 後台按 **Restore** 恢復（資料不會消失）。有孩子固定在玩就不會發生。暫停期間遊戲仍可離線玩，恢復後會自動補傳。
