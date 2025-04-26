// 电影评分功能
document.addEventListener("DOMContentLoaded", function () {
  // 处理评分表单提交
  const ratingForms = document.querySelectorAll(".rating-form");
  ratingForms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const formData = new FormData(form);
      fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            // 更新评分显示
            const movieCard = form.closest(".movie-card");
            if (movieCard) {
              const ratingDisplay = movieCard.querySelector(".rating-display");
              if (ratingDisplay) {
                ratingDisplay.textContent = `您的评分: ${formData.get(
                  "rating"
                )}`;
              }
            }
          }
        })
        .catch((error) => console.error("Error:", error));
    });
  });

  // 处理搜索表单
  const searchForm = document.querySelector("#search-form");
  if (searchForm) {
    searchForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const searchQuery = document.querySelector("#search-input").value;
      window.location.href = `/movies/search?q=${encodeURIComponent(
        searchQuery
      )}`;
    });
  }
});

// 图片加载错误处理
document.addEventListener("DOMContentLoaded", function () {
  const images = document.querySelectorAll("img");
  images.forEach((img) => {
    img.addEventListener("error", function () {
      this.src = "/static/images/default_poster.jpg";
    });
  });
});
