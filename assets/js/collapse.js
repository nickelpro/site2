
function collapseToggle(el) {
  var collapseDiv = el.parentElement.getElementsByClassName('collapse-div')[0];
  if(collapseDiv.clientHeight) {
    collapseDiv.style.height = 0;
  } else {
    var inner = collapseDiv.getElementsByClassName('collapse-inner')[0];
    var height = inner.clientHeight / parseFloat(getComputedStyle(
        document.querySelector('body'))['font-size'])
    collapseDiv.style.transitionDuration = Math.max(height/80, 0.4) + "s";
    collapseDiv.style.height = height + "rem";
  }
}

function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

function collapseClose(el) {
  var collapseDiv = el.parentElement.parentElement;
  var collapseTop = collapseDiv.parentElement.getElementsByClassName('collapse-button')[0];

  if(!isInViewport(collapseTop)) {
    window.scrollBy({
      left: 0, top: -collapseDiv.clientHeight, behavior: 'smooth'
    });
  }
  collapseDiv.style.height = 0;
}
