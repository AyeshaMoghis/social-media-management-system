// -------------------------------
// 🔹 Dropdown Toggle Logic
// -------------------------------
const dropdownBtn = document.getElementById("linkDropdownButton");
const dropdownMenu = document.getElementById("dropdownMenu");
const dropdownArrow = document.getElementById("dropdownArrow");

if (dropdownBtn) {
  dropdownBtn.addEventListener("click", () => {
    dropdownMenu.classList.toggle("hidden");
    dropdownArrow.classList.toggle("rotate-180");
  });

  // Close dropdown if clicking outside
  window.addEventListener("click", (e) => {
    if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
      dropdownMenu.classList.add("hidden");
      dropdownArrow.classList.remove("rotate-180");
    }
  });
}

// Smooth rotation for arrow
if (dropdownArrow) {
  dropdownArrow.style.transition = "transform 0.2s ease-in-out";
}

// -------------------------------
// 🔹 Auto Platform Icon + Colors
// -------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".card");

  cards.forEach((card) => {
    const titleEl = card.querySelector("h3");
    const iconEl = card.querySelector(".linkedin-icon");

    if (!titleEl || !iconEl) return;

    const platform = titleEl.textContent.trim().toLowerCase();

    if (platform.includes("linkedin")) {
      iconEl.textContent = "in";
      iconEl.style.backgroundColor = "#0077B5"; // LinkedIn Blue
    } 
    else if (platform.includes("twitter")) {
      iconEl.textContent = "t";
      iconEl.style.backgroundColor = "#1DA1F2"; // Twitter Blue
    } 
    else if (platform.includes("medium")) {
      iconEl.textContent = "M";
      iconEl.style.backgroundColor = "#000000"; // Medium Black
    }
  });
});

// -------------------------------
// 🔹 Optional: Refresh Animation
// -------------------------------
const refreshLinks = document.querySelectorAll('a[href^="/refresh-account/"]');
refreshLinks.forEach((link) => {
  link.addEventListener("click", (e) => {
    const btn = e.target;
    btn.textContent = "Refreshing...";
    btn.classList.add("opacity-70");
  });
});
