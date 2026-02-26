document.addEventListener('DOMContentLoaded', () => {
  // 模块名称和中文标题的映射
  const moduleTitles = {
    'education': '教育经历',
    'awards': '竞赛获奖',
    'projects': '项目经验',
    'honors': '校级荣誉',
    'others': '其他经历',
    'student': '学生工作',
    'practice': '社会实践'
  };

  // 读取模块列表并加载对应 HTML
  const modules = [
    'education',
    'awards',
    'projects',
    'honors',
    'others',
    'student',
    'practice'
  ];

  const navList = document.querySelector('.nav');
  const wrapper = document.getElementById('modules-wrapper');

  modules.forEach(moduleName => {
    // 创建导航链接
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = `#${moduleName}`;
    a.textContent = moduleTitles[moduleName] || moduleName;  // 如果没有映射，则使用英文名称
    li.appendChild(a);
    navList.appendChild(li);

    // 创建容器并加载模块 HTML
    const container = document.createElement('div');
    container.id = moduleName;
    container.className = 'section';
    wrapper.appendChild(container);

    // 动态加载对应模块的 HTML
    fetch(`${moduleName}/${moduleName}.html`)
      .then(response => response.text())
      .then(html => {
        container.innerHTML = html;
        // 加载完模块 HTML 后，为其中的图片容器启用轮播效果
        initImageGalleries(container);
      })
      .catch(err => {
        console.warn(`未能加载模块 ${moduleName}:`, err);
      });
  });

  // 初始化访问次数
  const visits = parseInt(localStorage.getItem('visitCount') || '0', 10) + 1;
  localStorage.setItem('visitCount', visits);
  const visitCounterElement = document.getElementById('visit-count');
  if (visitCounterElement) visitCounterElement.textContent = visits;
});

/**
 * 初始化一个父容器中的所有图片轮播。
 * @param {HTMLElement} scope - 包含图片容器的父节点
 */
function initImageGalleries(scope) {
  const galleries = scope.querySelectorAll('.image-container');
  galleries.forEach(container => {
    const images = Array.from(container.querySelectorAll('img'));
    if (images.length <= 1) return; // 无需轮播

    let current = 0; // 当前显示的图片
    let intervalId; // 用于存储 interval 的 ID

    // 更新图片显示
    const updateGallery = () => {
      images.forEach((img, i) => {
        img.style.opacity = i === current ? '1' : '0';  // 控制图片的显示/隐藏
      });
    };

    container.addEventListener('mouseenter', () => {
      current = 1;
      updateGallery();
      intervalId = setInterval(() => {
        current = (current + 1) % images.length;
        updateGallery();
      }, 1000);  // 每 1 秒切换一次图片
    });

    container.addEventListener('mouseleave', () => {
      clearInterval(intervalId);
      current = 0;
      updateGallery();
    });
  });
}
