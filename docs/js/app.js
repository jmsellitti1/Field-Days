const allData = {
    seasons: {},
    teams: [],
    days: [],
    metadata: {},
    rankings: {},
};

let activeGame = null;

function getPlayerName(player) {
    return player.Name || player['Name '] || player['(Name)'] || '';
}

function getPlayers() {
    return allData.metadata.players?.length
        ? allData.metadata.players
        : allData.teams.map(getPlayerName).filter(Boolean);
}

function parseRecord(record) {
    if (!record) return null;
    const match = String(record).match(/^(\d+)\s*-\s*(\d+)$/);
    return match ? { wins: Number(match[1]), losses: Number(match[2]) } : null;
}

function formatPercentage(record, percentage) {
    const parsed = parseRecord(record);
    if (!parsed || parsed.wins + parsed.losses === 0) return '-';
    if (typeof percentage === 'number') return `${(percentage * 100).toFixed(1)}%`;
    if (typeof percentage === 'string' && percentage.trim()) {
        const numeric = Number(percentage);
        return Number.isNaN(numeric) ? percentage : `${(numeric * 100).toFixed(1)}%`;
    }
    return `${(parsed.wins / (parsed.wins + parsed.losses) * 100).toFixed(1)}%`;
}

function buildStatsRow(player) {
    const name = getPlayerName(player);
    return `
        <td class="name-col name-col-first">${name}</td>
        <td>${player['Days Record'] || '-'}</td>
        <td>${formatPercentage(player['Days Record'], player['Days Pct'])}</td>
        <td>${player['Games Record'] || '-'}</td>
        <td>${formatPercentage(player['Games Record'], player['Games Pct'])}</td>
        <td>${player["PK's Record"] || '-'}</td>
        <td>${formatPercentage(player["PK's Record"], player["PK's Pct"])}</td>
        <td>${player['Cross Record'] || '-'}</td>
        <td>${formatPercentage(player['Cross Record'], player['Cross Pct'])}</td>
        <td>${player['A/D Record'] || '-'}</td>
        <td>${formatPercentage(player['A/D Record'], player['A/D Pct'])}</td>
        <td>${player['P&F Record'] || '-'}</td>
        <td>${formatPercentage(player['P&F Record'], player['P&F Pct'])}</td>
        <td>${player['SS Record'] || '-'}</td>
        <td>${formatPercentage(player['SS Record'], player['SS Pct'])}</td>
        <td>${player["FK's Record"] || '-'}</td>
        <td>${formatPercentage(player["FK's Record"], player["FK's Pct"])}</td>
        <td>${player.MVP || 0}</td>
        <td>${player.Clown || 0}</td>
        <td class="name-col name-col-last">${name}</td>
    `;
}

async function loadData() {
    try {
        const base = './data/';
        const [teamsRes, daysRes, seasonRes, metadataRes, rankingsRes] = await Promise.all([
            fetch(`${base}teams.json`),
            fetch(`${base}days.json`),
            fetch(`${base}season_stats.json`),
            fetch(`${base}metadata.json`),
            fetch(`${base}rankings.json`),
        ]);

        for (const [name, response] of [
            ['teams', teamsRes], ['days', daysRes], ['season stats', seasonRes],
            ['metadata', metadataRes], ['rankings', rankingsRes],
        ]) {
            if (!response.ok) throw new Error(`Failed to load ${name}: ${response.status}`);
        }

        allData.teams = await teamsRes.json();
        allData.days = await daysRes.json();
        allData.seasons = await seasonRes.json();
        allData.metadata = await metadataRes.json();
        allData.rankings = await rankingsRes.json();

        populateSeasonSelects();
        renderSeasonStats('total');
        renderRankings('total');
        renderTeams();
        renderDays();
        renderGameControls();
        renderGameStats();
    } catch (error) {
        document.body.innerHTML = `<div class="container"><p style="color:red">Error loading data: ${error.message}</p></div>`;
    }
}

function populateSeasonSelects() {
    const seasons = allData.metadata.seasons || [];
    const seasonSelect = document.getElementById('season-select');
    const gameSeasonSelect = document.getElementById('game-season-select');
    const rankingSeasonSelect = document.getElementById('ranking-season-select');

    for (const season of seasons) {
        seasonSelect.add(new Option(`${season} Season`, season));
        gameSeasonSelect.add(new Option(`${season} Season`, season));
        rankingSeasonSelect.add(new Option(`${season} Season`, season));
    }

    seasonSelect.addEventListener('change', event => renderSeasonStats(event.target.value));
    rankingSeasonSelect.addEventListener('change', event => renderRankings(event.target.value));
    gameSeasonSelect.addEventListener('change', renderGameStats);
}

function renderSeasonStats(season) {
    const tbody = document.querySelector('#season-stats-table tbody');
    tbody.innerHTML = '';
    for (const player of allData.seasons[season] || []) {
        const row = document.createElement('tr');
        row.innerHTML = buildStatsRow(player);
        tbody.appendChild(row);
    }
}

function renderRankings(season) {
    const tbody = document.querySelector('#rankings-table tbody');
    tbody.innerHTML = '';
    for (const player of allData.rankings[season] || []) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${player.rank}</td>
            <td>${player.name}</td>
            <td>${player.score.toFixed(1)}</td>
            <td>${player.average_opponent_rating}</td>
            <td>${player.day_record} (${player.days} days)</td>
            <td>${player.day_pct.toFixed(1)}%</td>
            <td>${player.game_pct.toFixed(1)}%</td>
            <td>${player.mvp}</td>
            <td>${player.clown}</td>
        `;
        tbody.appendChild(row);
    }
}

function getTeamRow(player) {
    return allData.teams.find(row => getPlayerName(row) === player);
}

function formatTeamFrequency(value) {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (trimmed.endsWith('%')) return trimmed;
        const numeric = Number(trimmed);
        return Number.isNaN(numeric) ? trimmed : `${(numeric * 100).toFixed(1)}%`;
    }
    return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '-';
}

function renderTeams() {
    const players = getPlayers();
    const thead = document.querySelector('#teams-table thead');
    const tbody = document.querySelector('#teams-table tbody');
    thead.innerHTML = `<tr><th class="corner-header">Players</th>${players.map(player => `<th class="player-header">${player}</th>`).join('')}</tr>`;
    tbody.innerHTML = players.map(rowPlayer => {
        const row = getTeamRow(rowPlayer);
        const cells = players.map(colPlayer => {
            const value = row?.[colPlayer];
            const display = formatTeamFrequency(value);
            return `<td class="${rowPlayer === colPlayer ? 'same-player combination-cell' : 'combination-cell'}">${display}</td>`;
        }).join('');
        return `<tr><td class="player-header">${rowPlayer}</td>${cells}</tr>`;
    }).join('');
}

function renderDays() {
    const tbody = document.querySelector('#days-table tbody');
    tbody.innerHTML = '';
    for (const day of allData.days) {
        const games = Array.from({ length: 10 }, (_, index) => day[`Game ${index + 1}`])
            .filter(Boolean)
            .join('<br>');
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${day.Date || '-'}</td>
            <td>${day['Team 1'] || '-'}</td>
            <td>${day['Team 2'] || '-'}</td>
            <td>${day.Score || '-'}</td>
            <td><small>${games || '-'}</small></td>
            <td>${day.MVP || '-'}</td>
            <td>${day['Clown of the Match'] || '-'}</td>
        `;
        tbody.appendChild(row);
    }
}

function gameNames() {
    const names = new Set();
    for (const day of allData.days) {
        for (let index = 1; index <= 10; index++) {
            const game = day[`Game ${index}`];
            if (game) {
                const match = String(game).match(/^(.+?) \(\d+-\d+\)$/);
                if (match) names.add(match[1]);
            }
        }
    }
    return [...names].sort();
}

function renderGameControls() {
    const container = document.getElementById('game-button-list');
    const names = gameNames();
    activeGame = names[0] || null;
    container.innerHTML = names.map(name =>
        `<button class="game-button${name === activeGame ? ' active' : ''}" data-game="${name}">${name}</button>`
    ).join('');
    container.addEventListener('click', event => {
        const button = event.target.closest('.game-button');
        if (!button) return;
        activeGame = button.dataset.game;
        container.querySelectorAll('.game-button').forEach(item =>
            item.classList.toggle('active', item === button)
        );
        renderGameStats();
    });
}

function renderGameStats() {
    if (!activeGame) return;
    const season = document.getElementById('game-season-select').value;
    const stats = {};

    for (const day of allData.days) {
        if (season !== 'total' && String(day.year) !== season) continue;
        const team1 = String(day['Team 1'] || '').split(',').map(name => name.trim()).filter(Boolean);
        const team2 = String(day['Team 2'] || '').split(',').map(name => name.trim()).filter(Boolean);

        for (let index = 1; index <= 10; index++) {
            const game = day[`Game ${index}`];
            const match = String(game || '').match(/^(.+?) \((\d+)-(\d+)\)$/);
            if (!match || match[1] !== activeGame) continue;
            const score1 = Number(match[2]);
            const score2 = Number(match[3]);

            for (const name of team1) {
                const row = stats[name] ||= { wins: 0, losses: 0 };
                row.wins += score1;
                row.losses += score2;
            }
            for (const name of team2) {
                const row = stats[name] ||= { wins: 0, losses: 0 };
                row.wins += score2;
                row.losses += score1;
            }
        }
    }

    const rows = Object.entries(stats)
        .map(([name, record]) => ({ name, ...record }))
        .filter(row => row.wins + row.losses > 0)
        .sort((a, b) =>
            (b.wins / (b.wins + b.losses)) - (a.wins / (a.wins + a.losses))
        );

    const tbody = document.querySelector('#game-stats-table tbody');
    tbody.innerHTML = rows.length ? rows.map(row => {
        const total = row.wins + row.losses;
        return `<tr><td>${row.name}</td><td>${row.wins}-${row.losses}</td><td>${(row.wins / total * 100).toFixed(1)}%</td></tr>`;
    }).join('') : '<tr><td colspan="3">No data available</td></tr>';
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(item => item.classList.remove('active'));
            document.querySelectorAll('section').forEach(section => section.classList.remove('active'));
            button.classList.add('active');
            document.getElementById(button.dataset.section).classList.add('active');
        });
    });
    loadData();
});
