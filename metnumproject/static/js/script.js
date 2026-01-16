   // ===============================
        // REFERENSI ELEMEN HTML
        // ===============================
        const form = document.getElementById("rootForm");
        const methodSelect = document.getElementById("method");

        const bisectionParams = document.getElementById("bisectionParams");
        const newtonParams = document.getElementById("newtonParams");

        const resultRoot = document.getElementById("rootValue");
        const resultFRoot = document.getElementById("fRootValue");
        const iterationCount = document.getElementById("iterationCount");
        const errorValue = document.getElementById("errorValue");

        const tableHeader = document.getElementById("tableHeader");
        const tableBody = document.getElementById("tableBody");

        const plotImage = document.getElementById("plotImage");
        const plotEmpty = document.getElementById("plotEmpty");

        const submitBtn = form.querySelector('button[type="submit"]');

        // ===============================
        // FUNGSI ANIMASI BACKGROUND
        // ===============================
        function createParticles() {
            const container = document.getElementById('bgAnimation');
            for (let i = 0; i < 20; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.width = Math.random() * 3 + 1 + 'px';
                particle.style.height = particle.style.width;
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDuration = Math.random() * 30 + 20 + 's';
                particle.style.animationDelay = Math.random() * 5 + 's';
                particle.style.background = Math.random() > 0.5 ? 'var(--accent-blue)' : 'var(--accent-green)';
                container.appendChild(particle);
            }
        }

        // ===============================
        // METHOD SELECTION
        // ===============================
        function selectMethod(method) {
            methodSelect.value = method;
            
            // Update tabs
            document.querySelectorAll('.method-tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            
            // Show/hide parameters
            if (method === 'bisection') {
                bisectionParams.style.display = 'grid';
                newtonParams.style.display = 'none';
            } else {
                bisectionParams.style.display = 'none';
                newtonParams.style.display = 'grid';
            }
        }

        // ===============================
        // ANIMASI COUNTER
        // ===============================
        function animateCounter(elementId, targetValue, isInteger = false) {
            const element = document.getElementById(elementId);
            const startValue = element.textContent === '-' ? 0 : parseFloat(element.textContent);
            const duration = 1000;
            const startTime = performance.now();
            
            function update(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                const easeOutQuart = 1 - Math.pow(1 - progress, 4);
                let currentValue;
                
                if (isInteger) {
                    currentValue = Math.floor(startValue + (targetValue - startValue) * easeOutQuart);
                } else {
                    currentValue = startValue + (parseFloat(targetValue) - startValue) * easeOutQuart;
                }
                
                if (isInteger) {
                    element.textContent = currentValue;
                } else {
                    element.textContent = parseFloat(currentValue).toFixed(6);
                }
                
                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    if (isInteger) {
                        element.textContent = targetValue;
                    } else {
                        element.textContent = parseFloat(targetValue).toFixed(6);
                    }
                }
            }
            
            requestAnimationFrame(update);
        }

        // ===============================
        // SHOW MESSAGE
        // ===============================
        function showMessage(text, type) {
            // Hapus pesan sebelumnya
            const existingMessage = document.querySelector('.message');
            if (existingMessage) existingMessage.remove();
            
            // Buat pesan baru
            const message = document.createElement('div');
            message.className = `message ${type}`;
            message.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${text}</span>
            `;
            
            // Tambahkan ke form
            document.querySelector('.actions').parentNode.insertBefore(message, document.querySelector('.actions'));
            
            // Hapus setelah 4 detik
            setTimeout(() => {
                message.style.opacity = '0';
                message.style.transform = 'translateX(20px)';
                setTimeout(() => message.remove(), 300);
            }, 4000);
        }

        // ===============================
        // TAMPILKAN PARAMETER SESUAI METODE
        // ===============================
        methodSelect.addEventListener("change", function () {
            if (this.value === "bisection") {
                bisectionParams.style.display = "block";
                newtonParams.style.display = "none";
            } else if (this.value === "newton") {
                bisectionParams.style.display = "none";
                newtonParams.style.display = "block";
            } else {
                bisectionParams.style.display = "none";
                newtonParams.style.display = "none";
            }
        });

        // ===============================
        // SUBMIT FORM
        // ===============================
        form.addEventListener("submit", function (e) {
            e.preventDefault();

            const method = methodSelect.value;

            let payload = {
                function: document.getElementById("function").value,
                method: method,
                tolerance: document.getElementById("tolerance").value,
                max_iter: document.getElementById("max_iter").value
            };

            if (method === "bisection") {
                payload.a = document.getElementById("a").value;
                payload.b = document.getElementById("b").value;
            } else if (method === "newton") {
                payload.x0 = document.getElementById("x0").value;
            } else {
                alert("Silakan pilih metode terlebih dahulu.");
                return;
            }

            // loading state tombol + reset grafik
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<div class="loading"></div> Menghitung...';
            }
            if (plotImage) {
                plotImage.style.display = "none";
                plotImage.removeAttribute("src");
            }
            if (plotEmpty) {
                plotEmpty.style.display = "grid";
                plotEmpty.textContent = "Sedang membuat grafik...";
            }

            fetch("/calculate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(data.error, "error");
                    return;
                }

                tampilkanHasil(data, method);
            })
            .catch(error => {
                console.error(error);
                showMessage("Terjadi kesalahan saat perhitungan.", "error");
            })
            .finally(() => {
                // kembalikan tombol ke normal
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.dataset.originalText || '<i class="fas fa-rocket"></i><span>Hitung Sekarang</span>';
                }
            });
        });

        // ===============================
        // TAMPILKAN HASIL
        // ===============================
        function tampilkanHasil(data, method) {
            // hasil utama dengan animasi
            animateCounter('rootValue', data.root);
            animateCounter('fRootValue', data.f_root);
            
            // Hitung jumlah iterasi
            const iterationCountValue = data.iterations.length;
            animateCounter('iterationCount', iterationCountValue, true);
            
            // Hitung error terakhir
            const lastError = data.iterations.length > 0 ? data.iterations[data.iterations.length - 1].error : 0;
            animateCounter('errorValue', lastError);

            // Tampilkan step-by-step process
            tampilkanSteps(data.steps);

            // bersihkan tabel
            tableHeader.innerHTML = "";
            tableBody.innerHTML = "";

            // header tabel
            let headers = [];

            if (method === "bisection") {
                headers = ["Iterasi", "a", "b", "c", "f(c)", "Error"];
            } else {
                headers = ["Iterasi", "x", "f(x)", "f'(x)", "Error"];
            }

            headers.forEach(h => {
                const th = document.createElement("th");
                th.textContent = h;
                tableHeader.appendChild(th);
            });

            // isi tabel dengan animasi
            data.iterations.forEach((row, index) => {
                setTimeout(() => {
                    const tr = document.createElement("tr");
                    tr.style.opacity = '0';
                    tr.style.transform = 'translateY(10px)';

                    if (method === "bisection") {
                        tr.innerHTML = `
                            <td>${row.iterasi}</td>
                            <td>${row.a.toFixed(6)}</td>
                            <td>${row.b.toFixed(6)}</td>
                            <td><strong style="color: var(--accent-blue);">${row.c.toFixed(6)}</strong></td>
                            <td>${row.f_c.toFixed(10)}</td>
                            <td>${row.error !== null ? row.error.toFixed(10) : "-"}</td>
                        `;
                    } else {
                        tr.innerHTML = `
                            <td>${row.iterasi}</td>
                            <td><strong style="color: var(--accent-blue);">${row.x.toFixed(6)}</strong></td>
                            <td>${row.f_x.toFixed(10)}</td>
                            <td>${row.df_x.toFixed(10)}</td>
                            <td>${row.error.toFixed(10)}</td>
                        `;
                    }

                    tableBody.appendChild(tr);
                    
                    // Animasi masuk
                    setTimeout(() => {
                        tr.style.transition = 'all 0.5s ease';
                        tr.style.opacity = '1';
                        tr.style.transform = 'translateY(0)';
                    }, 10);
                    
                }, index * 100);
            });

            // grafik
            plotImage.src = "data:image/png;base64," + data.plot;
            
            // tampilkan gambar & sembunyikan placeholder
            if (plotEmpty) plotEmpty.style.display = "none";
            plotImage.style.display = "block";

            // Animasi sukses
            showMessage(`🎯 Perhitungan berhasil! Akar ditemukan setelah ${iterationCountValue} iterasi.`, 'success');
        }

        // ===============================
        // TAMPILKAN STEP-BY-STEP PROCESS
        // ===============================
        function tampilkanSteps(steps) {
            const stepsContainer = document.getElementById('stepsContainer');
            stepsContainer.innerHTML = '';

            if (!steps || steps.length === 0) {
                stepsContainer.innerHTML = `
                    <div class="steps-empty">
                        <i class="fas fa-route" style="font-size: 3rem; margin-bottom: 1rem; color: var(--accent-blue);"></i>
                        <div>Tidak ada data step</div>
                    </div>
                `;
                return;
            }

            steps.forEach((step, index) => {
                setTimeout(() => {
                    const stepCard = document.createElement('div');
                    stepCard.className = `step-card ${step.status}`;
                    stepCard.style.animationDelay = `${index * 0.1}s`;

                    // Build details HTML
                    let detailsHTML = '';
                    if (step.details && step.details.length > 0) {
                        detailsHTML = '<div class="step-details">';
                        step.details.forEach(detail => {
                            detailsHTML += `<div class="step-detail-item">${detail}</div>`;
                        });
                        detailsHTML += '</div>';
                    }

                    // Status badge
                    let statusText = '';
                    if (step.status === 'init') statusText = 'Mulai';
                    else if (step.status === 'calculating') statusText = 'Hitung';
                    else if (step.status === 'converged') statusText = 'Konvergen';
                    else if (step.status === 'success') statusText = 'Selesai';

                    stepCard.innerHTML = `
                        <div class="step-header">
                            <div class="step-number">${step.step}</div>
                            <div class="step-title">
                                <h3>${step.title}</h3>
                                <p>${step.description}</p>
                            </div>
                        </div>
                        ${detailsHTML}
                        ${statusText ? `<div class="step-status-badge ${step.status}">${statusText}</div>` : ''}
                    `;

                    stepsContainer.appendChild(stepCard);
                }, index * 200);
            });
        }

        // ===============================
        // INISIALISASI
        // ===============================
        document.addEventListener('DOMContentLoaded', () => {
            createParticles();
            
            // Animasi saat halaman dimuat
            document.querySelectorAll('.card').forEach((card, index) => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px) scale(0.95)';
                
                setTimeout(() => {
                    card.style.transition = 'all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0) scale(1)';
                }, index * 200);
            });
            
            // Set default method
            selectMethod('bisection');
        });