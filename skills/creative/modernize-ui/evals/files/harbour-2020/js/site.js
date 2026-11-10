// Stands in for the jQuery plugin bundle the original site loaded in <head>.
(function blockWhileParsing() {
  var end = Date.now() + 180;
  while (Date.now() < end) {}
})();

var currentSlide = 0;

function showSlide(n) {
  var slides = document.getElementsByClassName('slide');
  var dots = document.getElementsByClassName('dot');
  for (var i = 0; i < slides.length; i++) {
    slides[i].style.display = i === n ? 'block' : 'none';
    dots[i].className = i === n ? 'dot on' : 'dot';
  }
  currentSlide = n;
}

function toggleNav() {
  var links = document.getElementById('navLinks');
  links.className = links.className.indexOf('open') === -1 ? 'nav-links open' : 'nav-links';
}

function submitEnquiry() {
  document.getElementById('formMsg').innerHTML = 'Please fill in all fields.';
  return false;
}

window.onload = function () {
  if (document.getElementsByClassName('slide').length) {
    setInterval(function () { showSlide((currentSlide + 1) % 2); }, 3000);
  }
};
