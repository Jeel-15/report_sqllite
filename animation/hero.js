const canvas = document.getElementById('particle-sphere');
const ctx = canvas.getContext('2d');

let width, height;
let particles = [];

// Configuration
const particleCount = 800; // Number of dots/characters
const sphereRadius = 300; // Size of the sphere
const fov = 350; // Field of view (depth perspective)
const characters = ['+', '-', '1', '0', '|', '·']; // The shapes to draw

function resize() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
}

// Generate points evenly distributed on a sphere
function initParticles() {
  particles = [];
  for (let i = 0; i < particleCount; i++) {
    // Math to distribute points on a 3D sphere
    const phi = Math.acos(-1 + (2 * i) / particleCount);
    const theta = Math.sqrt(particleCount * Math.PI) * phi;
    
    particles.push({
      x: sphereRadius * Math.cos(theta) * Math.sin(phi),
      y: sphereRadius * Math.sin(theta) * Math.sin(phi),
      z: sphereRadius * Math.cos(phi),
      char: characters[Math.floor(Math.random() * characters.length)]
    });
  }
}

let angleX = 0;
let angleY = 0;

function animate() {
  ctx.clearRect(0, 0, width, height);
  
  // Slowly rotate the sphere
  angleX += 0.001;
  angleY += 0.002;

  const cosX = Math.cos(angleX);
  const sinX = Math.sin(angleX);
  const cosY = Math.cos(angleY);
  const sinY = Math.sin(angleY);

  particles.forEach(p => {
    // Rotate around Y axis
    let x1 = p.x * cosY - p.z * sinY;
    let z1 = p.z * cosY + p.x * sinY;
    
    // Rotate around X axis
    let y2 = p.y * cosX - z1 * sinX;
    let z2 = z1 * cosX + p.y * sinX;

    // 3D to 2D Projection
    const scale = fov / (fov + z2);
    const x2d = (x1 * scale) + (width / 2);
    const y2d = (y2 * scale) + (height / 2);

    // Fade out particles that are in the back of the sphere
    const opacity = Math.max(0, Math.min(1, (z2 + sphereRadius) / (sphereRadius * 2)));

    // Draw the particle (using text characters like the video)
    ctx.font = `${10 * scale}px monospace`;
    ctx.fillStyle = `rgba(0, 0, 0, ${opacity * 0.5})`; // Black color with dynamic opacity
    ctx.fillText(p.char, x2d, y2d);
  });

  requestAnimationFrame(animate);
}

// Initialize
window.addEventListener('resize', resize);
resize();
initParticles();
animate();