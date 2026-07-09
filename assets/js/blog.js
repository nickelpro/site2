const themeStorageKey = 'blog-theme';

function preferredTheme() {
  const saved = localStorage.getItem(themeStorageKey);
  if (saved === 'dark' || saved === 'light') {
    return saved;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function syncThemedImages(theme) {
  const useDark = theme === 'dark';
  for (const image of document.querySelectorAll('[data-lightsrc]')) {
    const nextSrc = useDark ? image.dataset.darksrc || image.dataset.lightsrc : image.dataset.lightsrc;
    if (nextSrc) {
      image.src = nextSrc;
    }
  }
}

function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.body.classList.toggle('is-dark', isDark);
  document.body.dataset.theme = theme;
  syncThemedImages(theme);

  const button = document.querySelector('[data-theme-toggle]');
  if (button) {
    button.setAttribute('aria-pressed', String(isDark));
    const label = button.querySelector('[data-theme-label]');
    if (label) {
      label.textContent = isDark ? 'Day' : 'Night';
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  applyTheme(preferredTheme());

  const button = document.querySelector('[data-theme-toggle]');
  if (!button) {
    return;
  }

  button.addEventListener('click', () => {
    const nextTheme = document.body.classList.contains('is-dark') ? 'light' : 'dark';
    localStorage.setItem(themeStorageKey, nextTheme);
    applyTheme(nextTheme);
  });
});
