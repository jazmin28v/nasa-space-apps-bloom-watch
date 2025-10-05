document.addEventListener('DOMContentLoaded', () => {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const calendarPopup = document.getElementById('calendarPopup');
    const monthYearDisplay = document.getElementById('monthYear');
    const calendarDays = document.getElementById('calendarDays');
    const prevMonthBtn = document.getElementById('prevMonth');
    const nextMonthBtn = document.getElementById('nextMonth');

    let currentCalendarDate = new Date(); // La fecha del mes que se está mostrando en el calendario
    let activeInput = null; // Para saber qué input está activo (startDate o endDate)

    const months = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    // Formatea una fecha a "DD/MM/YYYY"
    function formatDate(date) {
        if (!date) return '';
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0'); // Meses son 0-index
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }

    // Parsea una fecha "DD/MM/YYYY" a un objeto Date
    function parseDate(dateString) {
        if (!dateString) return null;
        const parts = dateString.split('/');
        if (parts.length === 3) {
            // new Date(year, monthIndex, day)
            // monthIndex es 0-index, por eso parts[1] - 1
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const year = parseInt(parts[2], 10);
            return new Date(year, month, day);
        }
        return null;
    }

    // Normaliza una fecha para comparar solo día, mes y año (ignora la hora)
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

        // Obtener el primer día de la semana para el primer día del mes (0=Domingo, 1=Lunes...)
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        // Obtener el último día del mes
        const lastDayOfMonth = new Date(year, month + 1, 0).getDate();

        // Rellenar con días vacíos antes del primer día del mes
        for (let i = 0; i < firstDayOfMonth; i++) {
            const emptyDiv = document.createElement('div');
            emptyDiv.classList.add('empty');
            calendarDays.appendChild(emptyDiv);
        }

        // Crear los divs para cada día del mes
        for (let i = 1; i <= lastDayOfMonth; i++) {
            const dayDiv = document.createElement('div');
            dayDiv.textContent = i;
            dayDiv.classList.add('current-month');

            const today = normalizeDate(new Date());
            const currentDay = normalizeDate(new Date(year, month, i)); // Normalizar para comparación

            // Marcar el día actual
            if (currentDay.getTime() === today.getTime()) {
                dayDiv.classList.add('today');
            }

            // Marcar las fechas seleccionadas
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

            // Marcar el rango entre fechas
            if (normalizedStartDate && normalizedEndDate && currentDay > normalizedStartDate && currentDay < normalizedEndDate) {
                 dayDiv.classList.add('in-range');
            }

            dayDiv.addEventListener('click', () => {
                const clickedDate = new Date(year, month, i);

                if (activeInput === startDateInput) {
                    // Si ya hay una fecha de fin, asegúrate de que la fecha de inicio no sea posterior
                    const existingEndDate = parseDate(endDateInput.value);
                    if (existingEndDate && clickedDate > existingEndDate) {
                        alert('La fecha de inicio no puede ser posterior a la fecha de fin.');
                        return;
                    }
                    startDateInput.value = formatDate(clickedDate);
                } else if (activeInput === endDateInput) {
                    // Asegúrate de que la fecha de fin no sea anterior a la fecha de inicio
                    const start = parseDate(startDateInput.value);
                    if (start && clickedDate < start) {
                        alert('La fecha de fin no puede ser anterior a la fecha de inicio.');
                        return;
                    }
                    endDateInput.value = formatDate(clickedDate);
                }
                calendarPopup.style.display = 'none'; // Oculta el calendario después de seleccionar
                renderCalendar(); // Volver a renderizar para actualizar las selecciones visuales
            });

            calendarDays.appendChild(dayDiv);
        }
    }

    // Inicializar los inputs con la fecha de hoy
    const today = new Date();
    startDateInput.value = formatDate(today);
    // Para endDate, puedes poner una fecha por defecto o dejarla vacía
    const fiveDaysLater = new Date(today);
    fiveDaysLater.setDate(today.getDate() + 5);
    endDateInput.value = formatDate(fiveDaysLater);


    // Mostrar el calendario al hacer clic en los inputs
    startDateInput.addEventListener('click', () => {
        activeInput = startDateInput;
        calendarPopup.style.display = 'block';
        // Si ya hay una fecha en el input, el calendario se posiciona en ese mes
        const val = parseDate(startDateInput.value);
        currentCalendarDate = val || new Date(); // Si no hay fecha, usa la actual
        renderCalendar();
    });

    endDateInput.addEventListener('click', () => {
        activeInput = endDateInput;
        calendarPopup.style.display = 'block';
        // Si ya hay una fecha en el input, el calendario se posiciona en ese mes
        const val = parseDate(endDateInput.value);
        // Si no hay fecha de fin, intenta usar la de inicio. Si tampoco, usa la actual.
        currentCalendarDate = val || parseDate(startDateInput.value) || new Date();
        renderCalendar();
    });

    // Navegación del calendario
    prevMonthBtn.addEventListener('click', () => {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
        renderCalendar();
    });

    // Ocultar calendario si se hace clic fuera de él
    document.addEventListener('click', (event) => {
        // Asegúrate de que el clic no fue en los inputs o dentro del popup del calendario
        if (!calendarPopup.contains(event.target) && event.target !== startDateInput && event.target !== endDateInput) {
            calendarPopup.style.display = 'none';
        }
    });

    // Renderizar el calendario al cargar la página (inicialmente oculto)
    renderCalendar(); // Se renderiza para establecer la UI de los días
    calendarPopup.style.display = 'none'; // Pero se mantiene oculto al inicio
});