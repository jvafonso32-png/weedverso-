import fs from 'fs';
import { JSDOM } from 'jsdom';

const html = fs.readFileSync('d:/weedverso/app/index.html', 'utf8');
const dom = new JSDOM(html, { runScripts: "dangerously" });
const window = dom.window;
const document = window.document;

// Let it run the inline scripts
setTimeout(() => {
  console.log("Errors caught by JSDOM:");
  // JSDOM logs errors to its virtual console, let's just check if we can call renderAll()
  try {
    if(window.renderAll) {
      console.log("renderAll exists");
      window.renderAll();
      console.log("renderAll executed successfully");
    } else {
      console.log("renderAll not found");
    }
  } catch(e) {
    console.error("RUNTIME ERROR:", e);
  }
}, 1000);
