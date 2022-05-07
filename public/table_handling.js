const colWhite = [255, 255, 255]
const colRed = [230, 124, 115]
const colYellow = [255, 255, 0]
const colGreen = [87, 187, 138]

function init_table() {
    const channelTable = document.getElementById("telegram_channels")

    const tbody = channelTable.getElementsByTagName("tbody")[0]
    const countScale = (givenValue) => colourScale(colWhite, colGreen, 0, 1000, givenValue)
    const today = new Date()
    const old = new Date()
    old.setDate(old.getDate() - 180)
    const dateScale = (givenValue) => colourScale(colWhite, colRed, today, old, givenValue)
    let lastAnimal = null
    for (let channel of telegramChannels["channels"]) {
        const newAnimal = lastAnimal != null && channel["animal"] !== lastAnimal
        lastAnimal = channel["animal"]
        addRow(channel, tbody, newAnimal, countScale, dateScale)
    }
}

function clamp(min, max, value) {
    return Math.max(min, Math.min(max, value))
}
const clampRatio = (value) => clamp(0, 1, value)

function colourScale(startColour, endColour, startValue, endValue, givenValue) {
    const ratio = clampRatio((givenValue - startValue) / (endValue - startValue))
    const red = Math.round(startColour[0] + ratio * (endColour[0] - startColour[0]))
    const green = Math.round(startColour[1] + ratio * (endColour[1] - startColour[1]))
    const blue = Math.round(startColour[2] + ratio * (endColour[2] - startColour[2]))
    return `rgb(${red}, ${green}, ${blue})`
}

function addRow(channel, tableBody, newAnimal, countScale, dateScale) {
    const tr = document.createElement("tr")
    if (newAnimal) {
        tr.classList.add("new-animal")
    }
    const handleCell = document.createElement("td")
    handleCell.innerHTML = `<a href=${channel['link']}">@${channel['handle']}</a>`
    tr.appendChild(handleCell)

    const animalCell = document.createElement("td")
    animalCell.innerHTML = channel['animal']
    tr.appendChild(animalCell)

    const ownerCell = document.createElement("td")
    ownerCell.innerHTML = channel['owner']
    tr.appendChild(ownerCell)

    const picsCell = document.createElement("td")
    picsCell.innerHTML = channel['num_pics'] === null ? "?" : channel['num_pics']
    picsCell.style.backgroundColor = countScale(channel['num_pics'])
    tr.appendChild(picsCell)

    const gifsCell = document.createElement("td")
    gifsCell.innerHTML = channel['num_gifs'] === null ? "?" : channel['num_gifs']
    gifsCell.style.backgroundColor = countScale(channel['num_gifs'])
    tr.appendChild(gifsCell)

    const vidsCell = document.createElement("td")
    vidsCell.innerHTML = channel['num_vids'] === null ? "?" : channel['num_vids']
    vidsCell.style.backgroundColor = countScale(channel['num_vids'])
    tr.appendChild(vidsCell)

    const subsCell = document.createElement("td")
    subsCell.innerHTML = channel['num_subs'] === null ? "?" : channel['num_subs']
    subsCell.style.backgroundColor = countScale(channel['num_subs'])
    tr.appendChild(subsCell)

    const latestCell = document.createElement("td")
    latestCell.innerHTML = channel['latest_post'] === null ? "-" : channel['latest_post']
    if (channel['latest_post'] !== null) {
        latestCell.style.backgroundColor = dateScale(new Date(channel['latest_post']))
    }
    tr.appendChild(latestCell)

    const notesCell = document.createElement("td")
    notesCell.innerHTML = channel['notes']
    tr.appendChild(notesCell)
    tableBody.appendChild(tr)
}

init_table()