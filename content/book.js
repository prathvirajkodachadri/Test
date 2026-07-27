/*
 * BOOK CONTENT
 * ------------
 * This is the only file you need to edit to publish your own book.
 *
 * 1. Update the `meta` block with your title, author, and blurb.
 * 2. Replace the objects in `chapters` with your own.
 *    - `title`  : chapter title shown in the table of contents
 *    - `part`   : (optional) section/part label used to group chapters
 *    - `body`   : an array of HTML strings. Each string is one block.
 *                 Plain text becomes a paragraph automatically.
 *                 You may also pass raw HTML, e.g.
 *                   "<h3>A heading</h3>"
 *                   "<blockquote>A quotation.</blockquote>"
 *                   "<p class=\"break\">* * *</p>"
 *
 * Everything else (navigation, table of contents, progress) is generated.
 */

window.BOOK = {
  meta: {
    title: "The Lantern of Quiet Hours",
    subtitle: "A Novel in Eight Chapters",
    author: "A. Placeholder",
    year: 2026,
    blurb:
      "Sample content. Swap this text — and the chapters below — for your own manuscript in content/book.js.",
    // Optional: path to a cover image. Leave empty to use the generated cover.
    cover: ""
  },

  chapters: [
    {
      title: "The House on Ember Street",
      part: "Part One — Arrival",
      body: [
        "ನಾನು The house had been waiting a long time, and it had learned to wait well. Paint curled from the shutters in slow ribbons, and the porch boards had settled into a chord of complaint that sounded whenever the wind leaned against them.",
        "Mira arrived on a Tuesday with two suitcases and no clear plan. She had rehearsed a speech for the taxi driver about why a person leaves a city, but he had asked nothing at all, and so the speech stayed folded in her mouth like a letter never sent.",
        "<blockquote>Some houses are built. Others are simply agreed upon by everyone who has ever slept in them.</blockquote>",
        "Inside, the air smelled of cold stone and old paper. She set the suitcases down in the hallway and listened. Far off, in a room she had not yet found, something was ticking."
      ]
    },
    {
      title: "What the Ticking Was",
      part: "Part One — Arrival",
      body: [
        "It took her three days to find the clock, and when she did, it was not a clock at all but a lantern with a mechanism inside it, brass and patient, turning over one small tooth at a time.",
        "There was no flame. There had not been a flame for years, judging by the dust. And yet the glass was warm, faintly, the way a stone is warm an hour after the sun has gone.",
        "She carried it to the kitchen table and sat with it until dark, which came early that time of year, and arrived without ceremony.",
        "<p class=\"break\">* * *</p>",
        "At nine o'clock, the lantern lit itself."
      ]
    },
    {
      title: "A Neighbour, Briefly",
      part: "Part One — Arrival",
      body: [
        "The woman next door introduced herself as Edith and immediately began describing the neighbourhood as though reading from an inventory: the baker who closed on Thursdays, the road that flooded, the boy who delivered nothing but always knocked.",
        "\"You've got the Aldous house,\" Edith said at last, in a different voice. \"They all last about a season.\"",
        "\"And then?\"",
        "\"And then they go somewhere quieter.\" Edith smiled without unkindness. \"Or they stop needing quiet at all. Hard to say which is the better outcome.\""
      ]
    },
    {
      title: "The Hours That Do Not Count",
      part: "Part Two — The Lantern",
      body: [
        "Mira discovered that the lantern kept its own hours, and they did not correspond to anyone else's. It woke at nine and burned until some indeterminate point in the night, and in that interval the house behaved differently.",
        "Sound travelled further. A page turned upstairs could be heard in the cellar. Her own footsteps arrived a half-second before she took them, so that walking down the hall felt like following someone very like herself.",
        "She began writing things down, not because she expected to understand them, but because writing was the only argument she had ever won against fear."
      ]
    },
    {
      title: "Correspondence",
      part: "Part Two — The Lantern",
      body: [
        "The first letter appeared under the door on a morning with no post. It was addressed to the house rather than to her, and it began without greeting.",
        "<blockquote>You have found the lantern. Please do not move it to the second floor. — A.</blockquote>",
        "She moved it to the second floor.",
        "This, she would reflect later, was the moment the season properly began."
      ]
    },
    {
      title: "Second Floor, Nine O'Clock",
      part: "Part Two — The Lantern",
      body: [
        "The upstairs rooms had been shut so long that opening them felt less like entering and more like interrupting.",
        "At nine, the lantern lit, and the light did something it had not done downstairs: it fell in the wrong direction. Shadows pointed toward the flame instead of away from it, gathering at the glass like moths made of absence.",
        "Mira stood very still and counted her heartbeats until she reached a number she trusted. Then she picked the lantern up and carried it, slowly, to the window."
      ]
    },
    {
      title: "The Field Behind the House",
      part: "Part Three — Departure",
      body: [
        "From the upstairs window, she could see a field that did not exist from the ground. She checked twice, going down and up again, out of a stubbornness she recognised from childhood.",
        "It was ordinary in every respect — grass, a fence line, a single leaning tree — and that ordinariness was the most frightening thing about it. Wonders can be dismissed. A field cannot.",
        "In the morning she went outside and walked to where the field should have been and found only the neighbour's hedge and a bin left out too long, and she stood there feeling, absurdly, that she had been stood up."
      ]
    },
    {
      title: "Somewhere Quieter",
      part: "Part Three — Departure",
      body: [
        "On the last night, Mira set the lantern on the porch and sat beside it with a blanket over her knees, the way people used to sit before there was anything else to do.",
        "At nine, it lit. The light went out across the yard, and the shadows leaned in toward it, and the field appeared at the edge of everything like a held breath finally released.",
        "She did not walk into it. That is worth saying plainly, because the story is often told the other way.",
        "She sat until the mechanism wound down, and then she carried the lantern inside, wrote one line in her notebook, and slept better than she had in years.",
        "<blockquote>The line read: <em>It was only ever asking to be noticed.</em></blockquote>",
        "<p class=\"break\">THE END</p>"
      ]
    }
  ]
};
