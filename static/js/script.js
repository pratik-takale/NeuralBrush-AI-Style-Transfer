
'use strict';

function previewFile(input, previewId) {

    const preview = document.getElementById(previewId);

    const file = input.files[0];

    if (!file) return;

    // Validate image
    if (!file.type.startsWith('image/')) {

        alert('Please upload a valid image.');

        return;
    }

    // Create image preview URL
    const imageURL = URL.createObjectURL(file);

    preview.innerHTML =
        `<img src="${imageURL}" alt="Image Preview">`;
}


// ====================================
// DOM LOADED
// ====================================

document.addEventListener('DOMContentLoaded', function () {

    // Smooth scroll to result
    const resultSection =
        document.getElementById('resultSection');

    if (resultSection) {

        resultSection.scrollIntoView({
            behavior: 'smooth'
        });
    }


    // ====================================
    // PARTICLE BACKGROUND
    // ====================================

    const canvas =
        document.getElementById('neuralCanvas');

    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    let width;
    let height;

    let particles = [];

    let mouse = {
        x: null,
        y: null,
        radius: 150
    };


    function resize() {

        width = canvas.width = window.innerWidth;

        height = canvas.height = window.innerHeight;
    }


    class Particle {

        constructor() {

            this.x = Math.random() * width;

            this.y = Math.random() * height;

            this.vx = (Math.random() - 0.5) * 0.5;

            this.vy = (Math.random() - 0.5) * 0.5;

            this.size = Math.random() * 3 + 1.5;

            this.hue =
                Math.floor(Math.random() * 10) * 36;

            this.density =
                (Math.random() * 30) + 1;
        }

        update() {

            this.x += this.vx;

            this.y += this.vy;

            // Mouse interaction
            if (mouse.x != null) {

                let dx = mouse.x - this.x;

                let dy = mouse.y - this.y;

                let distance =
                    Math.sqrt(dx * dx + dy * dy);

                if (distance < mouse.radius) {

                    const forceDirectionX =
                        dx / distance;

                    const forceDirectionY =
                        dy / distance;

                    const force =
                        (mouse.radius - distance)
                        / mouse.radius;

                    const directionX =
                        forceDirectionX *
                        force *
                        this.density;

                    const directionY =
                        forceDirectionY *
                        force *
                        this.density;

                    this.x -= directionX;

                    this.y -= directionY;
                }
            }

            if (this.x < 0 || this.x > width)
                this.vx *= -1;

            if (this.y < 0 || this.y > height)
                this.vy *= -1;

            this.hue = (this.hue + 0.2) % 360;
        }

        draw() {

            ctx.fillStyle =
                `hsla(${this.hue}, 70%, 60%, 0.3)`;

            ctx.beginPath();

            ctx.arc(
                this.x,
                this.y,
                this.size,
                0,
                Math.PI * 2
            );

            ctx.fill();
        }
    }


    function initParticles() {

        particles = [];

        const numParticles =
            Math.floor(window.innerWidth / 25);

        for (let i = 0; i < numParticles; i++) {

            particles.push(new Particle());
        }
    }


    function animate() {

        ctx.clearRect(0, 0, width, height);

        particles.forEach((p, i) => {

            p.update();

            p.draw();

            for (
                let j = i + 1;
                j < particles.length;
                j++
            ) {

                const p2 = particles[j];

                const d = Math.hypot(
                    p.x - p2.x,
                    p.y - p2.y
                );

                if (d < 100) {

                    ctx.strokeStyle =
                        `hsla(${p.hue}, 70%, 60%, ${
                            0.15 * (1 - d / 100)
                        })`;

                    ctx.lineWidth = 1;

                    ctx.beginPath();

                    ctx.moveTo(p.x, p.y);

                    ctx.lineTo(p2.x, p2.y);

                    ctx.stroke();
                }
            }
        });

        requestAnimationFrame(animate);
    }


    // Resize
    window.addEventListener('resize', () => {

        resize();

        initParticles();
    });


    // Mouse movement
    window.addEventListener('mousemove', (event) => {

        mouse.x = event.clientX;

        mouse.y = event.clientY;
    });


    resize();

    initParticles();

    animate();


    // ====================================
    // RANGE SLIDER
    // ====================================

    const range =
        document.getElementById('alphaRange');

    const rangeValue =
        document.getElementById('rangeValue');


    function updateRange() {

        if (!range || !rangeValue) return;

        const val = range.value;

        const min = range.min || 0;

        const max = range.max || 1;

        const percentage =
            ((val - min) * 100) / (max - min);

        rangeValue.textContent = val;

        const thumbWidth = 24;

        const offset =
            thumbWidth / 2 -
            (percentage * thumbWidth / 100);

        rangeValue.style.left =
            `calc(${percentage}% + ${offset}px)`;


        range.style.background =
            `linear-gradient(
                to right,
                #818cf8 0%,
                #c084fc ${percentage}%,
                rgba(30, 41, 59, 0.8) ${percentage}%,
                rgba(30, 41, 59, 0.8) 100%
            )`;
    }


    if (range) {

        range.addEventListener(
            'input',
            updateRange
        );

        updateRange();
    }


    // ====================================
    // LOADER
    // ====================================

    const uploadForm =
        document.getElementById('uploadForm');

    if (uploadForm) {

        uploadForm.addEventListener(
            'submit',
            () => {

                document
                    .getElementById('loader')
                    .classList.add('active');
            }
        );
    }

});