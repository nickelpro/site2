function darkToggle() {
  const dark = document.body.classList.contains('dark-mode');
  if (dark) {
    document.body.classList.remove('dark-mode');
    localStorage.setItem('dark-mode', 'false');
    for (const el of document.querySelectorAll(`[data-lightsrc]`)) {
      el.src = el.getAttribute('data-lightsrc');
    }
  } else {
    document.body.classList.add('dark-mode');
    localStorage.setItem('dark-mode', 'true');
    for (const el of document.querySelectorAll(`[data-darksrc]`)) {
      el.src = el.getAttribute('data-darksrc');
    }
  }
}
