const colWhite = [255, 255, 255]
const colRed = [230, 124, 115]
const colYellow = [255, 255, 0]
const colGreen = [87, 187, 138]

function init_table() {
    const channelTable = document.getElementById("telegram_channels")
    const thead = channelTable.getElementsByTagName("thead")[0]
    const table = new Table(channelTable)
    for (let th of thead.querySelectorAll("th[data-sort-column]")) {
        th.addEventListener("click", () => {
            const column = th.getAttribute("data-sort-column")
            table.sortBy(column)
        })
        th.style.cursor = "pointer"
    }
    const platformSelect = document.getElementById("select_platform")
    platformSelect.addEventListener("change", () => {
        table.viewPlatform(platformSelect.value)
    })
    const animalSelect = document.getElementById("select_animal")
    animalSelect.addEventListener("change", () => {
        table.viewAnimal(animalSelect.value)
    })

    table.render()
}

const colSettings = {
    "handle": {
        "default_asc": true,
        "sort": (channels) => channels.sort((chanA, chanB) => chanA.handle.localeCompare(chanB.handle))
    },
    "animal": {
        "default_asc": true,
        "sort": (channels) => {
            const anyAnimals = channels.filter((chan) => chan.animal === "*")
                .sort((chanA, chanB) => chanA.handle.localeCompare(chanB.handle))
            const notAnimals = channels.filter((chan) => chan.animal === "~")
                .sort((chanA, chanB) => chanA.handle.localeCompare(chanB.handle))
            const other = channels.filter((chan) => !"*~".includes(chan.animal))
                .sort((chanA, chanB) => {
                    if (chanA.animal === chanB.animal) {
                        return chanA.handle.localeCompare(chanB.handle)
                    }
                    return chanA.animal.localeCompare(chanB.animal)
                })
            return [...anyAnimals, ...other, ...notAnimals]
        }
    },
    "owner": {
        "default_asc": true,
        "sort": (channels) => {
            const unknown = channels.filter((chan) => chan.owner === "?")
                .sort((chanA, chanB) => chanA.animal.localeCompare(chanB.animal))
            const known = channels.filter((chan) => chan.owner !== "?")
                .sort((chanA, chanB) => {
                    if (chanA.owner === chanB.owner) {
                        return chanA.animal.localeCompare(chanB.animal)
                    }
                    return chanA.owner.localeCompare(chanB.owner)
                })
            return [...known, ...unknown]
        }
    },
    "num_pics": {
        "default_asc": false,
        "sort": (channels) => channels.sort((chanA, chanB) => chanA["num_pics"] - chanB["num_pics"])
    },
    "num_gifs": {
        "default_asc": false,
        "sort": (channels) => channels.sort((chanA, chanB) => chanA["num_gifs"] - chanB["num_gifs"])
    },
    "num_vids": {
        "default_asc": false,
        "sort": (channels) => channels.sort((chanA, chanB) => chanA["num_vids"] - chanB["num_vids"])
    },
    "num_subs": {
        "default_asc": false,
        "sort": (channels) => channels.sort((chanA, chanB) => chanA["num_subs"] - chanB["num_subs"])
    },
    "latest_post": {
        "default_asc": false,
        "sort": (channels) => channels.sort(
            (chanA, chanB) => new Date(chanA["latest_post"]) - new Date(chanB["latest_post"])
        )
    }
}

class Table {
    constructor(tableElem) {
        this.tableElem = tableElem
        this.sort_by_col = "animal"
        this.sort_by_asc = true
        this.platform_types = ["telegram", "twitter"]
        this.view_animal = null
    }

    viewPlatform(platformType) {
        if (platformType === "all") {
            this.platform_types = ["telegram", "twitter"]
        } else {
            this.platform_types = [platformType]
        }
        this.render()
    }

    viewAnimal(animal) {
        if (animal === "all") {
            this.view_animal = null
        } else {
            this.view_animal = animal
        }
        this.render()
    }

    sortBy(column) {
        if (column === this.sort_by_col) {
            this.sort_by_asc = !this.sort_by_asc
        } else {
            this.sort_by_col = column
            this.sort_by_asc = colSettings[column].default_asc ?? true
        }
        this.render()
    }

    render() {
        // Update table headers to display ordering
        const thead = this.tableElem.getElementsByTagName("thead")[0]
        for (let th of thead.querySelectorAll("th[data-sort-column]")) {
            if (th.innerText.endsWith("▾") || th.innerText.endsWith("▴")) {
                th.innerText = th.innerText.slice(0, -1)
            }
            if (th.getAttribute("data-sort-column") === this.sort_by_col) {
                th.innerText += this.sort_by_asc ? "▴" : "▾"
            }
        }

        const tbody = document.createElement("tbody")
        // Build colour scales
        const countScale = (givenValue) => colourScale(colWhite, colGreen, 0, 1000, givenValue)
        const today = new Date()
        const old = new Date()
        old.setDate(old.getDate() - 180)
        const dateScale = (givenValue) => colourScale(colWhite, colRed, today, old, givenValue)

        // Filter channels to display
        const channels = telegramChannels["channels"]
        const filteredChannels = channels.filter((chan) => this.platform_types.includes(chan.platform))
            .filter((chan) => {
                if (this.view_animal === null) {
                    return true
                }
                return chan.animal === this.view_animal
        })
        // Sort channels
        const sortedChannels = colSettings[this.sort_by_col].sort(filteredChannels)
        if (!this.sort_by_asc) {
            sortedChannels.reverse()
        }

        let lastAnimal = null
        for (let channel of sortedChannels) {
            const newAnimal = lastAnimal != null && this.sort_by_col === "animal" && channel.animal !== lastAnimal
            lastAnimal = channel.animal
            addRow(channel, tbody, newAnimal, countScale, dateScale)
        }
        if (sortedChannels.length === 0) {
            const row = document.createElement("tr")
            const cell = document.createElement("td")
            cell.colSpan = 9
            cell.style.fontStyle = "italic"
            cell.style.textAlign = "center"
            cell.innerText = "There's nothing here..."
            row.appendChild(cell)
            tbody.appendChild(row)
        }
        this.tableElem.getElementsByTagName("tbody")[0].replaceWith(tbody)
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
    const platformCell = document.createElement("td")
    platformCell.innerHTML = `<img src="icon_${channel['platform']}.svg" alt="${channel['platform']}" style="height:1em"/>`
    tr.appendChild(platformCell)

    const handleCell = document.createElement("td")
    handleCell.innerHTML = `<a href="${channel['link']}" target="_blank">@${channel['handle']}</a>`
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