"use strict";


// ======================================================================
// Configuration
// ======================================================================

const ONLINE_TIMEOUT_MS = 10 * 60 * 1000;

const HISTORY_LIMIT = 1000;

const REFRESH_INTERVAL_MS = 30 * 1000;

const CHART_POINTS = 300;


// ======================================================================
// State
// ======================================================================

const charts = {};


// ======================================================================
// DOM
// ======================================================================

const devicesContainer =
    document.getElementById("devices");

const loadingElement =
    document.getElementById("loading");

const errorElement =
    document.getElementById("error");

const noDevicesElement =
    document.getElementById("no-devices");

const currentTimeElement =
    document.getElementById("current-time");

const lastUpdateElement =
    document.getElementById("last-update");


// ======================================================================
// Helpers
// ======================================================================

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ======================================================================
// Local time
// ======================================================================

function formatLocalTime(value) {

    if (!value) {
        return "—";
    }

    let date;

    if (typeof value === "number") {

        date = new Date(
            value * 1000
        );

    } else {

        let stringValue = String(value);

        /*
         * Наш backend хранит timestamps в UTC.
         *
         * API исторически возвращает:
         *
         * 2026-08-05T08:42:20
         *
         * Добавляем Z, чтобы браузер
         * правильно перевёл UTC → локальное время.
         */

        if (
            !stringValue.endsWith("Z") &&
            !stringValue.includes("+")
        ) {
            stringValue += "Z";
        }

        date = new Date(
            stringValue
        );
    }

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "—";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}


function formatLocalDateTime(value) {

    if (!value) {
        return "—";
    }

    let stringValue = String(value);

    if (
        !stringValue.endsWith("Z") &&
        !stringValue.includes("+")
    ) {
        stringValue += "Z";
    }

    const date = new Date(
        stringValue
    );

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "—";
    }

    return new Intl.DateTimeFormat(
        undefined,
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        }
    ).format(date);
}


// ======================================================================
// Current browser time
// ======================================================================

function updateCurrentTime() {

    const now = new Date();

    currentTimeElement.textContent =
        new Intl.DateTimeFormat(
            undefined,
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }
        ).format(now);
}


// ======================================================================
// Online / Offline
// ======================================================================

function isDeviceOnline(lastSeen) {

    if (!lastSeen) {
        return false;
    }

    let value = String(lastSeen);

    if (
        !value.endsWith("Z") &&
        !value.includes("+")
    ) {
        value += "Z";
    }

    const timestamp =
        new Date(value).getTime();

    if (
        Number.isNaN(timestamp)
    ) {
        return false;
    }

    const age =
        Date.now() - timestamp;

    return (
        age >= 0 &&
        age < ONLINE_TIMEOUT_MS
    );
}


// ======================================================================
// Number formatting
// ======================================================================

function formatTemperature(value) {

    if (value === null || value === undefined) {
        return "—";
    }

    return `${Number(value).toFixed(1)} °C`;
}


function formatHumidity(value) {

    if (value === null || value === undefined) {
        return "—";
    }

    return `${Number(value).toFixed(1)} %`;
}


function formatBattery(value) {

    if (value === null || value === undefined) {
        return "—";
    }

    return `${Number(value).toFixed(2)} V`;
}


// ======================================================================
// API
// ======================================================================

async function fetchJson(url) {

    const response = await fetch(
        url,
        {
            cache: "no-store",
        }
    );

    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status}: ${url}`
        );
    }

    return response.json();
}


// ======================================================================
// Devices
// ======================================================================

async function loadDevices() {

    const data =
        await fetchJson(
            "/api/devices"
        );

    return data.devices || [];
}


// ======================================================================
// History
// ======================================================================

async function loadHistory(deviceName) {

    const data =
        await fetchJson(
            `/api/readings?device=${encodeURIComponent(deviceName)}&limit=${HISTORY_LIMIT}`
        );

    return data.readings || [];
}

// ======================================================================
// Normalize time
// ======================================================================

function normalizeTimestamp(timestamp) {
    let value = String(timestamp);
    if (!value.endsWith("Z") && !value.includes("+")) {
        value += "Z";
    }
    return value;
}

// ======================================================================
// 24 hours filtering
// ======================================================================

function last24Hours(readings) {

    const now =
        Date.now();

    const from =
        now - 24 * 60 * 60 * 1000;

    return readings
        .filter(
            reading => {

                if (!reading.timestamp) {
                    return false;
                }

                let value =
                    String(
                        reading.timestamp
                    );

                if (
                    !value.endsWith("Z") &&
                    !value.includes("+")
                ) {
                    value += "Z";
                }

                const timestamp =
                    new Date(value).getTime();

                return (
                    !Number.isNaN(timestamp) &&
                    timestamp >= from &&
                    timestamp <= now
                );
            }
        )
        .sort(
            (a, b) =>
                new Date(normalizeTimestamp(a.timestamp)) -
                new Date(normalizeTimestamp(b.timestamp))
        );
}


// ======================================================================
// Chart preparation
// ======================================================================

function chartData(
    readings,
    field
) {

    const filtered =
        last24Hours(
            readings
        );

    /*
     * Чтобы очень большое количество
     * точек не перегружало браузер.
     */

    let points = filtered;

    if (
        filtered.length > CHART_POINTS
    ) {

        const step =
            filtered.length /
            CHART_POINTS;

        points = [];

        for (
            let i = 0;
            i < CHART_POINTS;
            i++
        ) {

            points.push(
                filtered[
                    Math.floor(i * step)
                ]
            );
        }
    }

    const labels = [];
    const values = [];

    for (const reading of points) {

        let timestamp =
            String(
                reading.timestamp
            );

        if (
            !timestamp.endsWith("Z") &&
            !timestamp.includes("+")
        ) {
            timestamp += "Z";
        }

        const date =
            new Date(timestamp);

        labels.push(
            date.toLocaleTimeString(
                undefined,
                {
                    hour: "2-digit",
                    minute: "2-digit",
                }
            )
        );

        const value =
            reading[field];

        values.push(
            value === null ||
            value === undefined
                ? null
                : Number(value)
        );
    }

    return {
        labels,
        values,
    };
}


// ======================================================================
// Chart.js
// ======================================================================

function createChart(
    canvas,
    readings,
    field,
    label,
    color,
    unit
) {

    const data =
        chartData(
            readings,
            field
        );

    return new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: data.labels,

                datasets: [
                    {
                        label,

                        data: data.values,

                        borderColor: color,

                        backgroundColor: color,

                        borderWidth: 2,

                        pointRadius: 0,

                        pointHoverRadius: 4,

                        tension: 0.25,

                        spanGaps: true,

                        fill: false,
                    },
                ],
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                interaction: {
                    intersect: false,

                    mode: "index",
                },

                plugins: {
                    legend: {
                        display: true,
                    },

                    tooltip: {
                        callbacks: {
                            label(context) {

                                const value =
                                    context.parsed.y;

                                if (
                                    value === null ||
                                    value === undefined
                                ) {
                                    return "Нет данных";
                                }

                                return `${label}: ${value.toFixed(2)} ${unit}`;
                            },
                        },
                    },
                },

                scales: {
                    x: {
                        ticks: {
                            maxTicksLimit: 8,
                        },
                    },

                    y: {
                        beginAtZero: false,

                        ticks: {
                            callback(value) {
                                return `${value} ${unit}`;
                            },
                        },
                    },
                },
            },
        }
    );
}


// ======================================================================
// Destroy old charts
// ======================================================================

function destroyDeviceCharts(
    deviceId
) {

    const existing =
        charts[deviceId];

    if (!existing) {
        return;
    }

    for (
        const chart of Object.values(existing)
    ) {

        if (chart) {
            chart.destroy();
        }
    }

    delete charts[deviceId];
}


// ======================================================================
// Device card
// ======================================================================

function createDeviceCard(
    device
) {

    const latest =
        device.latest;

    const online =
        isDeviceOnline(
            device.last_seen
        );

    const statusClass =
        online
            ? "online"
            : "offline";

    const statusText =
        online
            ? "ONLINE"
            : "OFFLINE";

    const card =
        document.createElement(
            "section"
        );

    card.className =
        "device-card";

    card.dataset.deviceId =
        device.id;

    card.innerHTML = `

        <div class="device-header">

            <div>

                <h2>
                    ${escapeHtml(device.name)}
                </h2>

                <div class="device-id">
                    ID: ${device.id}
                </div>

            </div>

            <div class="status ${statusClass}">

                <span class="status-dot"></span>

                <span>
                    ${statusText}
                </span>

            </div>

        </div>


        <div class="device-meta">

            <div>

                <span class="meta-label">
                    Последний контакт
                </span>

                <strong>
                    ${formatLocalDateTime(device.last_seen)}
                </strong>

            </div>

            <div>

                <span class="meta-label">
                    Обновлено
                </span>

                <strong>
                    ${
                        latest
                            ? formatLocalDateTime(
                                latest.timestamp
                            )
                            : "—"
                    }
                </strong>

            </div>

        </div>


        <div class="metrics">

            <div class="metric">

                <div class="metric-icon temperature-icon">
                    🌡️
                </div>

                <div>

                    <div class="metric-label">
                        Температура
                    </div>

                    <div class="metric-value">
                        ${
                            latest
                                ? formatTemperature(
                                    latest.temperature
                                )
                                : "—"
                        }
                    </div>

                </div>

            </div>


            <div class="metric">

                <div class="metric-icon humidity-icon">
                    💧
                </div>

                <div>

                    <div class="metric-label">
                        Влажность
                    </div>

                    <div class="metric-value">
                        ${
                            latest
                                ? formatHumidity(
                                    latest.humidity
                                )
                                : "—"
                        }
                    </div>

                </div>

            </div>


            <div class="metric">

                <div class="metric-icon battery-icon">
                    🔋
                </div>

                <div>

                    <div class="metric-label">
                        Батарея
                    </div>

                    <div class="metric-value">
                        ${
                            latest
                                ? formatBattery(
                                    latest.battery
                                )
                                : "—"
                        }
                    </div>

                </div>

            </div>

        </div>


        <div class="charts">

            <div class="chart-card">

                <h3>
                    Температура — последние 24 часа
                </h3>

                <div class="chart-container">

                    <canvas
                        id="temperature-${device.id}"
                    ></canvas>

                </div>

            </div>


            <div class="chart-card">

                <h3>
                    Влажность — последние 24 часа
                </h3>

                <div class="chart-container">

                    <canvas
                        id="humidity-${device.id}"
                    ></canvas>

                </div>

            </div>


            <div class="chart-card">

                <h3>
                    Батарея — последние 24 часа
                </h3>

                <div class="chart-container">

                    <canvas
                        id="battery-${device.id}"
                    ></canvas>

                </div>

            </div>

        </div>

    `;

    devicesContainer.appendChild(
        card
    );

    return card;
}


// ======================================================================
// Render device
// ======================================================================

async function renderDevice(
    device
) {

    const card =
        createDeviceCard(
            device
        );

    try {

        const readings =
            await loadHistory(
                device.name
            );

        const temperatureCanvas =
            card.querySelector(
                `#temperature-${device.id}`
            );

        const humidityCanvas =
            card.querySelector(
                `#humidity-${device.id}`
            );

        const batteryCanvas =
            card.querySelector(
                `#battery-${device.id}`
            );


        destroyDeviceCharts(
            device.id
        );


        charts[device.id] = {};


        /*
         * Температура — КРАСНАЯ
         */

        charts[device.id].temperature =
            createChart(
                temperatureCanvas,
                readings,
                "temperature",
                "Температура",
                "#dc2626",
                "°C"
            );


        /*
         * Влажность — ГОЛУБАЯ
         */

        charts[device.id].humidity =
            createChart(
                humidityCanvas,
                readings,
                "humidity",
                "Влажность",
                "#0ea5e9",
                "%"
            );


        /*
         * Батарея — ЗЕЛЁНАЯ
         */

        charts[device.id].battery =
            createChart(
                batteryCanvas,
                readings,
                "battery",
                "Батарея",
                "#16a34a",
                "V"
            );

    } catch (error) {

        console.error(
            `Ошибка загрузки ${device.name}:`,
            error
        );
    }
}


// ======================================================================
// Render all devices
// ======================================================================

async function renderDevices() {

    try {

        hideError();

        const devices =
            await loadDevices();


        loadingElement.classList.add(
            "hidden"
        );


        if (
            devices.length === 0
        ) {

            devicesContainer.innerHTML = "";

            noDevicesElement.classList.remove(
                "hidden"
            );

            return;
        }


        noDevicesElement.classList.add(
            "hidden"
        );


        /*
         * Удаляем старые карточки.
         */

        devicesContainer.innerHTML = "";


        /*
         * Старые графики уничтожаем,
         * чтобы Chart.js не создавал
         * утечки памяти.
         */

        for (
            const deviceId of Object.keys(charts)
        ) {

            destroyDeviceCharts(
                deviceId
            );
        }


        /*
         * Рисуем каждый датчик.
         */

        for (
            const device of devices
        ) {

            await renderDevice(
                device
            );
        }


        lastUpdateElement.textContent =
            `Данные обновлены: ${formatLocalTime(new Date())}`;

    } catch (error) {

        console.error(
            error
        );

        loadingElement.classList.add(
            "hidden"
        );

        showError(
            "Не удалось получить данные с сервера."
        );
    }
}


// ======================================================================
// Error
// ======================================================================

function showError(
    message
) {

    errorElement.textContent =
        message;

    errorElement.classList.remove(
        "hidden"
    );
}


function hideError() {

    errorElement.textContent =
        "";

    errorElement.classList.add(
        "hidden"
    );
}


// ======================================================================
// Start
// ======================================================================

async function start() {

    updateCurrentTime();

    setInterval(
        updateCurrentTime,
        1000
    );

    await renderDevices();

    setInterval(
        renderDevices,
        REFRESH_INTERVAL_MS
    );
}


start();