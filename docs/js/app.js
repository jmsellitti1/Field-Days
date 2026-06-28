// Global data storage
let allData = {
    stats: [],
    seasons: {},
    teams: [],
    days: [],
    metadata: {}
};

function getPlayerName(player) {
    return player.Name || player['Name '] || player['(Name)'] || '';
}

function parseRecord(record) {
    if (!record || record === '-') return null;
    const match = String(record).trim().match(/^(\d+)\s*-\s*(\d+)$/);
    if (!match) return null;
    return { wins: parseInt(match[1], 10), losses: parseInt(match[2], 10) };
}

function hasRecordExperience(record) {
    const parsed = parseRecord(record);
    return parsed !== null && parsed.wins + parsed.losses > 0;
}

function formatStatPercentage(record, pct) {
    if (!hasRecordExperience(record)) return '-';

    if (pct === null || pct === undefined || pct === '') {
        const parsed = parseRecord(record);
        if (parsed) {
            const total = parsed.wins + parsed.losses;
            return `${((parsed.wins / total) * 100).toFixed(1)}%`;
        }
        return '-';
    }

    if (typeof pct === 'string') {
        const trimmed = pct.trim();
        if (trimmed.endsWith('%')) return trimmed;
        const numeric = Number(trimmed);
        if (!Number.isNaN(numeric)) return `${(numeric * 100).toFixed(1)}%`;
        return trimmed;
    }

    if (typeof pct === 'number') {
        return `${(pct * 100).toFixed(1)}%`;
    }

    return '-';
}

function formatTeamFrequency(value) {
    if (value === null || value === undefined || value === '' || value === '-') return '-';
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (trimmed.endsWith('%')) return trimmed;
        const numeric = Number(trimmed);
        if (!Number.isNaN(numeric)) return `${(numeric * 100).toFixed(1)}%`;
        return trimmed;
    }
    if (typeof value === 'number') {
        return `${(value * 100).toFixed(1)}%`;
    }
    return value;
}

// Load all data from JSON files
async function loadData() {
    try {
        const dataPath = './data/';
        const [statsRes, teamsRes, daysRes, seasonStatsRes, metadataRes] = await Promise.all([
            fetch(`${dataPath}stats.json`),
            fetch(`${dataPath}teams.json`),
            fetch(`${dataPath}days.json`),
            fetch(`${dataPath}season_stats.json`),
            fetch(`${dataPath}metadata.json`)
        ]);

        if (!statsRes.ok) throw new Error(`Failed to load stats: ${statsRes.status}`);
        if (!teamsRes.ok) throw new Error(`Failed to load teams: ${teamsRes.status}`);
        if (!daysRes.ok) throw new Error(`Failed to load days: ${daysRes.status}`);
        if (!seasonStatsRes.ok) throw new Error(`Failed to load season stats: ${seasonStatsRes.status}`);
        if (!metadataRes.ok) throw new Error(`Failed to load metadata: ${metadataRes.status}`);

        allData.stats = await statsRes.json();
        allData.teams = await teamsRes.json();
        allData.days = await daysRes.json();
        allData.seasons = await seasonStatsRes.json();
        allData.metadata = await metadataRes.json();

        populateSeasonDropdown();
        renderOverallStats();
        renderTeams();
        renderDays();
        renderSeasonStats('total');
    } catch (error) {
        console.error('Error loading data:', error);
        document.body.innerHTML = `<div class="container"><p style="color: red; margin-top: 2rem;">Error loading data: ${error.message}</p></div>`;
    }
}

// Populate season dropdown
function populateSeasonDropdown() {
    const select = document.getElementById('season-select');
    select.innerHTML = '<option value="total">All Time</option>';
    
    if (allData.metadata.seasons) {
        allData.metadata.seasons.forEach(season => {
            const option = document.createElement('option');
            option.value = season;
            option.textContent = `${season} Season`;
            select.appendChild(option);
        });
    }
    
    select.addEventListener('change', (e) => {
        renderSeasonStats(e.target.value);
    });
}

function buildStatsRow(player) {
    const name = getPlayerName(player);
    return `
        <td class="name-col name-col-first">${name}</td>
        <td>${player['Days Record'] || '-'}</td>
        <td>${formatStatPercentage(player['Days Record'], player['Days Pct'])}</td>
        <td>${player['Games Record'] || '-'}</td>
        <td>${formatStatPercentage(player['Games Record'], player['Games Pct'])}</td>
        <td>${player["PK's Record"] || '-'}</td>
        <td>${formatStatPercentage(player["PK's Record"], player["PK's Pct"])}</td>
        <td>${player['Cross Record'] || '-'}</td>
        <td>${formatStatPercentage(player['Cross Record'], player['Cross Pct'])}</td>
        <td>${player['A/D Record'] || '-'}</td>
        <td>${formatStatPercentage(player['A/D Record'], player['A/D Pct'])}</td>
        <td>${player['P&F Record'] || '-'}</td>
        <td>${formatStatPercentage(player['P&F Record'], player['P&F Pct'])}</td>
        <td>${player['SS Record'] || '-'}</td>
        <td>${formatStatPercentage(player['SS Record'], player['SS Pct'])}</td>
        <td>${player["FK's Record"] || '-'}</td>
        <td>${formatStatPercentage(player["FK's Record"], player["FK's Pct"])}</td>
        <td>${player.MVP || 0}</td>
        <td>${player.Clown || 0}</td>
        <td class="name-col name-col-last">${name}</td>
    `;
}

// Render overall stats table
function renderOverallStats() {
    const tbody = document.querySelector('#stats-table tbody');
    tbody.innerHTML = '';

    allData.stats.forEach(player => {
        const row = document.createElement('tr');
        row.innerHTML = buildStatsRow(player);
        tbody.appendChild(row);
    });
}

// Render season stats
function renderSeasonStats(season) {
    const tbody = document.querySelector('#season-stats-table tbody');
    tbody.innerHTML = '';

    const seasonData = allData.seasons[season] || [];
    
    seasonData.forEach(player => {
        const row = document.createElement('tr');
        row.innerHTML = buildStatsRow(player);
        tbody.appendChild(row);
    });
}

// Render teams table
function renderTeams() {
    const container = document.querySelector('#teams-table');
    
    if (!allData.teams || allData.teams.length === 0) {
        container.innerHTML = '<tr><td>No team data available</td></tr>';
        return;
    }

    const players = Object.keys(allData.teams[0] || {}).filter(key => !['Name', '(Name)', 'Player A', 'Player B'].includes(key));
    
    // Create header
    const thead = container.querySelector('thead');
    let headerHTML = '<tr><th class="corner-header">Players</th>';
    players.forEach(player => {
        headerHTML += `<th class="player-header">${player}</th>`;
    });
    headerHTML += '</tr>';
    thead.innerHTML = headerHTML;

    // Create body
    const tbody = container.querySelector('tbody');
    tbody.innerHTML = '';
    
    allData.teams.forEach(row => {
        const playerName = row.Name || '';
        let rowHTML = `<tr><td class="player-header">${playerName}</td>`;
        
        players.forEach(player => {
            const value = row[player];
            const cellClass = playerName === player ? 'same-player combination-cell' : 'combination-cell';
            rowHTML += `<td class="${cellClass}">${value !== null && value !== undefined ? formatTeamFrequency(value) : '-'}</td>`;
        });
        
        rowHTML += '</tr>';
        tbody.innerHTML += rowHTML;
    });
}

// Render days/game history table
function renderDays() {
    const tbody = document.querySelector('#days-table tbody');
    tbody.innerHTML = '';

    allData.days.forEach(day => {
        const row = document.createElement('tr');
        
        let gamesHTML = '';
        if (day.Game) {
            gamesHTML = day.Game;
        } else {
            // Try to construct from individual game columns
            for (let i = 1; i <= 10; i++) {
                const gameCol = `Game ${i}`;
                if (day[gameCol]) {
                    gamesHTML += (gamesHTML ? '<br>' : '') + day[gameCol];
                }
            }
        }

        row.innerHTML = `
            <td>${day.Date || '-'}</td>
            <td>${day['Team 1'] || '-'}</td>
            <td>${day['Team 2'] || '-'}</td>
            <td>${day.Score || '-'}</td>
            <td><small>${gamesHTML ? gamesHTML.replace(/\n/g, '<br>') : '-'}</small></td>
            <td>${day.MVP || '-'}</td>
            <td>${day['Clown of the Match'] || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Navigation buttons
document.addEventListener('DOMContentLoaded', () => {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and sections
            navButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('section').forEach(section => section.classList.remove('active'));
            
            // Add active class to clicked button and corresponding section
            button.classList.add('active');
            const sectionId = button.getAttribute('data-section');
            document.getElementById(sectionId).classList.add('active');
        });
    });

    // Load all data on page load
    loadData();
});
