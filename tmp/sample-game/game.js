const GAME_DURATION_SECONDS = 30;

const arena = document.querySelector("#arena");
const target = document.querySelector("#target");
const scoreElement = document.querySelector("#score");
const timeLeftElement = document.querySelector("#time-left");
const comboElement = document.querySelector("#combo");
const statusElement = document.querySelector("#status");
const startButton = document.querySelector("#start-button");
const resetButton = document.querySelector("#reset-button");

let score = 0;
let combo = 0;
let bestCombo = 0;
let timeLeft = GAME_DURATION_SECONDS;
let timerId = null;
let running = false;

function updateUi() {
  scoreElement.textContent = String(score);
  timeLeftElement.textContent = String(timeLeft);
  comboElement.textContent = String(bestCombo);
}

function moveTarget() {
  const arenaRect = arena.getBoundingClientRect();
  const targetSize = target.offsetWidth;
  const maxX = Math.max(0, arenaRect.width - targetSize);
  const maxY = Math.max(0, arenaRect.height - targetSize);
  const x = Math.floor(Math.random() * maxX);
  const y = Math.floor(Math.random() * maxY);

  target.style.left = `${x + targetSize / 2}px`;
  target.style.top = `${y + targetSize / 2}px`;
}

function stopGame(message) {
  running = false;
  target.disabled = true;
  startButton.disabled = false;
  window.clearInterval(timerId);
  timerId = null;
  statusElement.textContent = message;
}

function resetGame() {
  score = 0;
  combo = 0;
  bestCombo = 0;
  timeLeft = GAME_DURATION_SECONDS;
  target.disabled = true;
  startButton.disabled = false;
  window.clearInterval(timerId);
  timerId = null;
  running = false;
  statusElement.textContent = "点击“开始游戏”后，尽可能快地收集星星。";
  updateUi();
  moveTarget();
}

function startGame() {
  if (running) {
    return;
  }

  score = 0;
  combo = 0;
  bestCombo = 0;
  timeLeft = GAME_DURATION_SECONDS;
  running = true;
  target.disabled = false;
  startButton.disabled = true;
  statusElement.textContent = "游戏进行中：点击星星！";
  updateUi();
  moveTarget();

  timerId = window.setInterval(() => {
    timeLeft -= 1;
    updateUi();

    if (timeLeft <= 0) {
      stopGame(`时间到！最终得分 ${score}，最高连击 ${bestCombo}。`);
    }
  }, 1000);
}

function collectStar() {
  if (!running) {
    return;
  }

  combo += 1;
  bestCombo = Math.max(bestCombo, combo);
  score += 10 + Math.min(combo, 10);
  statusElement.textContent = `命中！当前连击 ${combo}。`;
  updateUi();
  moveTarget();
}

target.addEventListener("click", collectStar);
startButton.addEventListener("click", startGame);
resetButton.addEventListener("click", resetGame);
arena.addEventListener("pointerleave", () => {
  if (running) {
    combo = 0;
    statusElement.textContent = "鼠标离开区域，连击已重置。";
  }
});

resetGame();
