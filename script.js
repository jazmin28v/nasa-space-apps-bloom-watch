document.addEventListener('DOMContentLoaded', () => {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const calendarPopup = document.getElementById('calendarPopup');
    const monthYearDisplay = document.getElementById('monthYear');
    const calendarDays = document.getElementById('calendarDays');
    const prevMonthBtn = document.getElementById('prevMonth');
    const nextMonthBtn = document.getElementById('nextMonth');

    let currentCalendarDate = new Date();
    let activeInput = null;

    const months = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    function formatDate(date) {
        if (!date) return '';
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }

    function parseDate(dateString) {
        if (!dateString) return null;
        const parts = dateString.split('/');
        if (parts.length === 3) {
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const year = parseInt(parts[2], 10);
            return new Date(year, month, day);
        }
        return null;
    }

    function normalizeDate(date) {
        if (!date) return null;
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        return d;
    }

    function renderCalendar() {
        calendarDays.innerHTML = '';
        const year = currentCalendarDate.getFullYear();
        const month = currentCalendarDate.getMonth();

        monthYearDisplay.textContent = `${months[month]} ${year}`;

        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const lastDayOfMonth = new Date(year, month + 1, 0).getDate();

        for (let i = 0; i < firstDayOfMonth; i++) {
            const emptyDiv = document.createElement('div');
            emptyDiv.classList.add('empty');
            calendarDays.appendChild(emptyDiv);
        }

        for (let i = 1; i <= lastDayOfMonth; i++) {
            const dayDiv = document.createElement('div');
            dayDiv.textContent = i;
            dayDiv.classList.add('current-month');

            const today = normalizeDate(new Date());
            const currentDay = normalizeDate(new Date(year, month, i));

            if (currentDay.getTime() === today.getTime()) {
                dayDiv.classList.add('today');
            }

            const startDate = parseDate(startDateInput.value);
            const endDate = parseDate(endDateInput.value);

            const normalizedStartDate = normalizeDate(startDate);
            const normalizedEndDate = normalizeDate(endDate);

            if (normalizedStartDate && currentDay.getTime() === normalizedStartDate.getTime()) {
                dayDiv.classList.add('selected');
            }
            if (normalizedEndDate && currentDay.getTime() === normalizedEndDate.getTime()) {
                dayDiv.classList.add('selected');
            }

            if (normalizedStartDate && normalizedEndDate && currentDay > normalizedStartDate && currentDay < normalizedEndDate) {
                dayDiv.classList.add('in-range');
            }

            dayDiv.addEventListener('click', () => {
                const clickedDate = new Date(year, month, i);

                if (activeInput === startDateInput) {
                    const existingEndDate = parseDate(endDateInput.value);
                    if (existingEndDate && clickedDate > existingEndDate) {
                        alert('La fecha de inicio no puede ser posterior a la fecha de fin.');
                        return;
                    }
                    startDateInput.value = formatDate(clickedDate);
                } else if (activeInput === endDateInput) {
                    const start = parseDate(startDateInput.value);
                    if (start && clickedDate < start) {
                        alert('La fecha de fin no puede ser anterior a la fecha de inicio.');
                        return;
                    }
                    endDateInput.value = formatDate(clickedDate);
                }
                calendarPopup.style.display = 'none';
                renderCalendar();
            });

            calendarDays.appendChild(dayDiv);
        }
    }

    const today = new Date();
    startDateInput.value = formatDate(today);
    const fiveDaysLater = new Date(today);
    fiveDaysLater.setDate(today.getDate() + 5);
    endDateInput.value = formatDate(fiveDaysLater);

    startDateInput.addEventListener('click', () => {
        activeInput = startDateInput;
        calendarPopup.style.display = 'block';
        const val = parseDate(startDateInput.value);
        currentCalendarDate = val || new Date();
        renderCalendar();
    });

    endDateInput.addEventListener('click', () => {
        activeInput = endDateInput;
        calendarPopup.style.display = 'block';
        const val = parseDate(endDateInput.value);
        currentCalendarDate = val || parseDate(startDateInput.value) || new Date();
        renderCalendar();
    });

    prevMonthBtn.addEventListener('click', () => {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
        renderCalendar();
    });

    document.addEventListener('click', (event) => {
        if (!calendarPopup.contains(event.target) && event.target !== startDateInput && event.target !== endDateInput) {
            calendarPopup.style.display = 'none';
        }
    });

    renderCalendar();
    calendarPopup.style.display = 'none';

    // 🔗 Función para enviar coordenadas + fechas al backend
    async function procesarAnalisis() {
        const lat = 25.6866;  // Reemplazar con input real
        const lon = -100.3161;

        const fechaInicio = startDateInput.value;
        const fechaFin = endDateInput.value;

        const convertirFecha = (fechaStr) => {
            const partes = fechaStr.split('/');
            return `${partes[2]}-${partes[1]}-${partes[0]}`;
        };

        const payload = {
            latitud: lat,
            longitud: lon,
            fecha_inicio: convertirFecha(fechaInicio),
            fecha_fin: convertirFecha(fechaFin)
        };

        try {
            const response = await fetch('http://localhost:8000/analizar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Error en la API');

            const resultado = await response.json();

            document.getElementById('resultado').innerHTML = `
                <h3>🌱 Diagnóstico de Cultivo</h3>
                <p><strong>Estado:</strong> ${resultado.diagnostico}</p>
                <p><strong>Probabilidad:</strong> ${resultado.probabilidad}%</p>
                <p><strong>NDVI:</strong> ${resultado.ndvi}</p>
                <p><strong>EVI:</strong> ${resultado.evi}</p>
                <p><strong>LST:</strong> ${resultado.lst} °C</p>
                <p><strong>Humedad:</strong> ${resultado.humedad} mm</p>
                <p><strong>Tmax:</strong> ${resultado.tmax} °C</p>
                <p><strong>Tmin:</strong> ${resultado.tmin} °C</p>
            `;
        } catch (error) {
            console.error('Error:', error);
            document.getElementById('resultado').innerHTML = `<p style="color:red;">Error al obtener el diagnóstico.</p>`;
        }
    }

    // Exponer la función al botón
    window.procesarAnalisis = procesarAnalisis;
});