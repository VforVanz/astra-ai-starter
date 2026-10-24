const USERS_KEY = "astra_users";
const SESSION_KEY = "astra_session";

function getUsers() {
  try { return JSON.parse(localStorage.getItem(USERS_KEY) || "[]"); }
  catch { return []; }
}

function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function showMessage(text, type = "error") {
  const box = document.getElementById("message");
  box.textContent = text;
  box.className = `auth-message ${type}`;
}

function setupPasswordButtons() {
  document.querySelectorAll(".show-password").forEach(button => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.target);
      const visible = input.type === "text";
      input.type = visible ? "password" : "text";
      button.textContent = visible ? "Tampilkan" : "Sembunyikan";
    });
  });
}

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", event => {
    event.preventDefault();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const password = document.getElementById("password").value;
    const user = getUsers().find(item => item.email === email && item.password === password);

    if (!user) {
      showMessage("Email atau password tidak cocok.");
      return;
    }

    localStorage.setItem(SESSION_KEY, JSON.stringify({
      name: user.name,
      email: user.email,
      role: user.role || "Member",
      loginAt: new Date().toISOString()
    }));

    showMessage("Login berhasil. Membuka dashboard...", "success");
    setTimeout(() => location.href = "index.html", 400);
  });
}

const registerForm = document.getElementById("registerForm");
if (registerForm) {
  registerForm.addEventListener("submit", event => {
    event.preventDefault();
    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("confirmPassword").value;
    const users = getUsers();

    if (password.length < 8) {
      showMessage("Password minimal 8 karakter.");
      return;
    }
    if (password !== confirm) {
      showMessage("Konfirmasi password tidak sama.");
      return;
    }
    if (users.some(user => user.email === email)) {
      showMessage("Email tersebut sudah terdaftar. Silakan login.");
      return;
    }

    users.push({ name, email, password, role: "Member", createdAt: new Date().toISOString() });
    saveUsers(users);
    showMessage("Registrasi berhasil. Mengarahkan ke halaman login...", "success");
    setTimeout(() => location.href = "login.html", 700);
  });
}

setupPasswordButtons();
