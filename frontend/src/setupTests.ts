/// <reference types="@testing-library/jest-dom" />
import '@testing-library/jest-dom'; 

// Stub scrollIntoView since jsdom does not implement it
window.HTMLElement.prototype.scrollIntoView = function() {}; 

/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck 