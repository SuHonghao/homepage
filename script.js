document.addEventListener('DOMContentLoaded', () => {
  initImageGalleries(document);
  const counter = document.getElementById('visit-count');
  if (!counter) return;
  // 隐私模式或禁用存储时，不影响页面其余功能。
  try {
    const previous = Number(localStorage.getItem('visitCount'));
    const visits = (Number.isSafeInteger(previous) && previous >= 0 ? previous : 0) + 1;
    localStorage.setItem('visitCount', String(visits));
    counter.textContent = String(visits);
  } catch {
    counter.textContent = '不可用';
  }
});

function initImageGalleries(scope) {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const stopGalleries = [];
  scope.querySelectorAll('.image-container').forEach(container => {
    const images = Array.from(container.querySelectorAll('img'));
    if (images.length <= 1) return;
    let current = 0;
    let intervalId = null;
    const show = index => {
      images[current].style.opacity = '0';
      current = index;
      images[current].style.opacity = '1';
    };
    const stop = () => {
      clearInterval(intervalId);
      intervalId = null;
      show(0);
    };
    const next = () => {
      const index = (current + 1) % images.length;
      // 图片未解码完成时保留当前图片，避免切换成白屏。
      if (images[index].complete && images[index].naturalWidth > 0) show(index);
    };
    container.addEventListener('mouseenter', () => {
      if (reducedMotion.matches || document.hidden || intervalId !== null) return;
      next();
      intervalId = setInterval(next, 2000);
    });
    container.addEventListener('mouseleave', stop);
    stopGalleries.push(stop);
  });
  const stopAll = () => stopGalleries.forEach(stop => stop());
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopAll();
  });
  window.addEventListener('pagehide', stopAll);
  reducedMotion.addEventListener('change', stopAll);
}
