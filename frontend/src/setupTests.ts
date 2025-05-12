import '@testing-library/jest-dom'; 

// Stub scrollIntoView since jsdom does not implement it
window.HTMLElement.prototype.scrollIntoView = function() {}; 