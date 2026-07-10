function setSrcToAttr(dataname) {
  for (const el of document.querySelectorAll(`[${dataname}]`)) {
    el.src = el.getAttribute(dataname);
  }
}

function setViewportVars() {
  const docEl = document.documentElement;
  const viewportWidth = docEl.clientWidth;
  const contentColumn = document.querySelector('article.post') || document.querySelector('.container');
  const contentColumnWidth = contentColumn ? contentColumn.clientWidth : viewportWidth;

  docEl.style.setProperty('--viewport-width', `${viewportWidth}px`);
  docEl.style.setProperty('--content-column-width', `${contentColumnWidth}px`);
}

window.addEventListener('DOMContentLoaded', () => {
  setViewportVars();
  const dark = localStorage.getItem('dark-mode');
  if (dark == null) {
    localStorage.setItem('dark-mode', 'false');
    setSrcToAttr('data-lightsrc');
  } else if (dark === 'true') {
    document.body.classList.add('dark-mode');
    setSrcToAttr('data-darksrc');
  }
  document.body.style.visibility = 'visible';
  document.body.style.opacity = 1;
  window.requestAnimationFrame(() => {
    document.body.style.transition = 'color 1s';
    document.body.style.transition = 'background-color 1s'
  });
});

window.addEventListener('resize', setViewportVars);
