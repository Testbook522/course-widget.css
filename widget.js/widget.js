(function () {
  "use strict";

  var widget = document.getElementById("tbCourseWidget");
  if (!widget) return;

  var CATEGORY = widget.dataset.category || "category";
  var DATA_URL = widget.dataset.dataUrl || ("./data/" + CATEGORY + ".json");
  var TITLE = widget.dataset.title || "Active Courses";
  var SUBTITLE = widget.dataset.subtitle || "Explore active courses or select an exam.";
  var CURRENT_YEAR = new Date().getFullYear();
  var heightFrame = 0;

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function escapeHtml(value) {
    var div = document.createElement("div");
    div.textContent = String(value || "");
    return div.innerHTML;
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/"/g, "&quot;");
  }

  function parseSheetDate(value) {
    if (!value) return null;
    var text = String(value).trim();
    var match = text.match(/Date\((\d+),(\d+),(\d+)(?:,(\d+),(\d+),(\d+))?\)/);
    if (match) {
      return new Date(
        Number(match[1]), Number(match[2]), Number(match[3]),
        Number(match[4] || 0), Number(match[5] || 0), Number(match[6] || 0)
      );
    }
    var date = new Date(text.replace(" ", "T"));
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isActiveCourse(course) {
    var delisted = normalize(course.isDelisted);
    if (delisted !== "false" && delisted !== "0") return false;
    if (!String(course.title || "").trim() || !String(course.url || "").trim()) return false;
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var release = parseSheetDate(course.releaseDate);
    var expiry = parseSheetDate(course.expiryDate);
    if (release && release > today) return false;
    if (expiry && expiry < today) return false;
    return true;
  }

  function extractYears(value) {
    var years = [];
    (String(value || "").match(/\b20\d{2}\b/g) || []).forEach(function (year) {
      years.push(Number(year));
    });
    return Array.from(new Set(years));
  }

  function courseYearScore(course) {
    var years = extractYears(course.title);
    if (years.indexOf(CURRENT_YEAR) !== -1) return 3;
    if (years.some(function (year) { return year > CURRENT_YEAR; })) return 2;
    if (!years.length) return 1;
    return 0;
  }

  function compareCourses(a, b) {
    var yearDifference = courseYearScore(b) - courseYearScore(a);
    if (yearDifference) return yearDifference;
    var ad = parseSheetDate(a.releaseDate);
    var bd = parseSheetDate(b.releaseDate);
    return ((bd ? bd.getTime() : 0) - (ad ? ad.getTime() : 0)) ||
      String(a.title || "").localeCompare(String(b.title || ""));
  }

  function cleanExamName(value) {
    var text = String(value || "").trim();
    if (!text) return "";
    text = text
      .replace(/\b20\d{2}\s*[-/]\s*(?:20)?\d{2}\b/gi, " ")
      .replace(/\b20\d{2}\b/gi, " ")
      .replace(/[|:_]+/g, " ")
      .replace(/\s{2,}/g, " ")
      .trim();
    if (!text || /^[\s\-–—/().]+$/.test(text)) return "";
    if (/^RRB\s*[- ]?JE\b/i.test(text)) return "RRB JE";
    if (/^SSC\s*[- ]?JE\b/i.test(text)) return "SSC JE";
    if (/^GATE\b/i.test(text)) return "GATE";
    return text;
  }

  function deriveExamFromTitle(title) {
    var text = String(title || "");
    var known = [
      [/\bRRB\s*[- ]?JE\b/i, "RRB JE"],
      [/\bSSC\s*[- ]?JE\b/i, "SSC JE"],
      [/\bGATE\b/i, "GATE"],
      [/\bUGC\s*NET\b/i, "UGC NET"],
      [/\bIBPS\s+(?:PO|CLERK|SO|RRB)\b/i, "IBPS"],
      [/\bSBI\s+(?:PO|CLERK)\b/i, "SBI"],
      [/\b(?:UPSC|IAS)\b/i, "UPSC"],
      [/\b(?:NEET|JEE|CTET|NDA|CDS|AFCAT)\b/i, function (match) { return match[0].toUpperCase(); }],
      [/\bRPSC\b/i, "RPSC"],
      [/\bBPSC\b/i, "BPSC"],
      [/\bMPSC\b/i, "MPSC"],
      [/\b(?:KVS|NVS)\b/i, function (match) { return match[0].toUpperCase(); }],
      [/\b(?:RAILWAY|RAILWAYS|RRB)\b/i, "Railways"]
    ];
    for (var i = 0; i < known.length; i += 1) {
      var match = text.match(known[i][0]);
      if (match) return typeof known[i][1] === "function" ? known[i][1](match) : known[i][1];
    }
    return cleanExamName(text.replace(/\b(course|batch|coaching|online|test\s*series|mock\s*test|study\s*material)\b/gi, " "));
  }

  function getExamName(course) {
    var target = cleanExamName(course.targetName);
    if (target) return target;
    var group = cleanExamName(course.group);
    if (group) return group;
    return deriveExamFromTitle(course.title) || "Other Courses";
  }

  function getUniqueExams(courses) {
    var unique = {};
    courses.forEach(function (course) {
      var exam = getExamName(course);
      if (exam && exam !== "Other Courses") unique[normalize(exam)] = exam;
    });
    return Object.keys(unique).map(function (key) { return unique[key]; })
      .sort(function (a, b) { return a.localeCompare(b); });
  }

  function addUtmParameters(rawUrl, course) {
    if (!rawUrl) return "#";
    try {
      var url = new URL(rawUrl);
      url.searchParams.set("utm_source", "testbook");
      url.searchParams.set("utm_medium", "course_widget");
      url.searchParams.set("utm_campaign", CATEGORY + "_courses");
      url.searchParams.set("utm_content", normalize(getExamName(course) || course.title).replace(/[^a-z0-9]+/g, "_"));
      return url.toString();
    } catch (_) {
      return rawUrl;
    }
  }

  function createCard(course) {
    var exam = getExamName(course);
    var searchText = [course.title, exam, course.group, course.language, course.type].filter(Boolean).join(" ");
    var image = course.image || "";
    return "<article class=\"tb-course-card\" data-exam=\"" + escapeAttribute(normalize(exam)) +
      "\" data-search=\"" + escapeAttribute(normalize(searchText)) + "\">" +
      (image ? "<img class=\"tb-course-image\" src=\"" + escapeAttribute(image) + "\" alt=\"" + escapeAttribute(course.title) + "\" loading=\"lazy\">" : "") +
      "<div class=\"tb-course-body\"><span class=\"tb-course-label\">Featured</span>" +
      "<h3 class=\"tb-course-title\">" + escapeHtml(course.title) + "</h3>" +
      "<div class=\"tb-course-meta\">" + escapeHtml([course.language, course.type].filter(Boolean).join(" · ")) + "</div>" +
      "<a class=\"tb-course-button\" href=\"" + escapeAttribute(addUtmParameters(course.url, course)) +
      "\" target=\"_blank\" rel=\"noopener noreferrer\">View Course</a></div></article>";
  }

  function bindWidgetEvents() {
    var track = widget.querySelector(".tb-course-track");
    var select = widget.querySelector(".tb-course-select");
    var search = widget.querySelector(".tb-course-search");
    var cards = Array.from(widget.querySelectorAll(".tb-course-card"));
    var emptyMessage = widget.querySelector("[data-empty-message]");
    if (!track || !select || !search) return;

    function filterCards() {
      var selectedExam = normalize(select.value);
      var searchTerm = normalize(search.value);
      var visibleCount = 0;
      cards.forEach(function (card) {
        var examMatches = !selectedExam || normalize(card.dataset.exam) === selectedExam;
        var searchMatches = !searchTerm || normalize(card.dataset.search).indexOf(searchTerm) !== -1;
        var show = examMatches && searchMatches;
        card.hidden = !show;
        if (show) visibleCount += 1;
      });
      emptyMessage.style.display = visibleCount ? "none" : "block";
      track.scrollLeft = 0;
      reportWidgetHeight();
    }

    select.addEventListener("change", filterCards);
    search.addEventListener("input", filterCards);
    widget.querySelector(".tb-course-prev").addEventListener("click", function () {
      track.scrollBy({ left: -450, behavior: "smooth" });
    });
    widget.querySelector(".tb-course-next").addEventListener("click", function () {
      track.scrollBy({ left: 450, behavior: "smooth" });
    });
  }

  function reportWidgetHeight() {
    cancelAnimationFrame(heightFrame);
    heightFrame = requestAnimationFrame(function () {
      var height = Math.ceil((widget.getBoundingClientRect().bottom || document.body.scrollHeight) + 8);
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: "tb-course-widget-height", height: height, category: CATEGORY }, "*");
      }
    });
  }

  function watchImages() {
    widget.querySelectorAll("img").forEach(function (image) {
      if (image.complete) reportWidgetHeight();
      image.addEventListener("load", reportWidgetHeight, { once: true });
      image.addEventListener("error", reportWidgetHeight, { once: true });
    });
  }

  function renderWidget(courses) {
    var exams = getUniqueExams(courses);
    widget.innerHTML = "<div class=\"tb-course-header\"><div class=\"tb-course-heading\"><h2>" +
      escapeHtml(TITLE) + "</h2><p>" + escapeHtml(SUBTITLE) + "</p></div>" +
      "<div class=\"tb-course-controls\"><select class=\"tb-course-select\" aria-label=\"Select exam\"><option value=\"\">All Active Courses</option>" +
      exams.map(function (exam) { return "<option value=\"" + escapeAttribute(normalize(exam)) + "\">" + escapeHtml(exam) + "</option>"; }).join("") +
      "</select><input type=\"search\" class=\"tb-course-search\" placeholder=\"Search course...\" aria-label=\"Search course\"></div></div>" +
      "<div class=\"tb-course-slider\"><button type=\"button\" class=\"tb-course-nav tb-course-prev\" aria-label=\"Previous courses\">‹</button>" +
      "<div class=\"tb-course-track\">" + courses.map(createCard).join("") + "</div>" +
      "<div class=\"tb-course-message\" data-empty-message style=\"display:none;\">No matching courses found.</div>" +
      "<button type=\"button\" class=\"tb-course-nav tb-course-next\" aria-label=\"Next courses\">›</button></div>";
    bindWidgetEvents();
    watchImages();
    reportWidgetHeight();
  }

  function showError(message) {
    widget.innerHTML = "<div class=\"tb-course-message tb-course-error\">" + escapeHtml(message) + "</div>";
    reportWidgetHeight();
  }

  if ("ResizeObserver" in window) {
    var observer = new ResizeObserver(reportWidgetHeight);
    observer.observe(widget);
  }
  window.addEventListener("load", reportWidgetHeight);
  window.addEventListener("resize", reportWidgetHeight);
  setTimeout(reportWidgetHeight, 200);
  setTimeout(reportWidgetHeight, 900);

  fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("Course data HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      var raw = Array.isArray(data) ? data : (Array.isArray(data.courses) ? data.courses : []);
      var courses = raw.filter(isActiveCourse).sort(compareCourses);
      if (!courses.length) {
        showError("No active courses found.");
        return;
      }
      renderWidget(courses);
    })
    .catch(function (error) {
      console.error("Course data load error:", error);
      showError("Courses could not be loaded.");
    });
})();
