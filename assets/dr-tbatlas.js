/*
 * Prokaryotic clean-up for the embedded JBrowse 2 build (TASK-09).
 *
 * Mycobacterium tuberculosis has no splicing, so intron controls are
 * meaningless here. The annotation served to the browser is already flattened
 * to one feature per locus, which removes the intron entries from the
 * "show sequence feature" dropdown at the source. The bundled JBrowse build
 * additionally renders an intron field and explanatory notes in its feature
 * sequence settings dialog regardless of the feature shape; this script hides
 * those, while leaving the upstream/downstream flanking controls untouched.
 */
(function () {
    "use strict";

    var INTRON = /intron/i;
    var ATTR = "data-drtbatlas-hidden";

    function hide(element) {
        if (!element || element.getAttribute(ATTR)) {
            return;
        }
        element.setAttribute(ATTR, "intron");
        element.style.display = "none";
    }

    function labelText(field) {
        var label = field.querySelector("label");
        return label ? label.textContent || "" : "";
    }

    function scrub(root) {
        if (!root || !root.querySelectorAll) {
            return;
        }

        // Sequence type options, whether rendered as a native select or as a
        // MUI menu.
        root.querySelectorAll("option, li[role='option'], .MuiMenuItem-root")
            .forEach(function (item) {
                if (INTRON.test(item.textContent || "")) {
                    hide(item);
                }
            });

        // The "number of intronic bases" field in the settings dialog. The
        // sibling up/down stream field is deliberately left alone.
        root.querySelectorAll(".MuiTextField-root, .MuiFormControl-root")
            .forEach(function (field) {
                if (INTRON.test(labelText(field))) {
                    hide(field);
                }
            });

        // Explanatory notes that only describe intron behaviour.
        root.querySelectorAll("p.MuiTypography-root, .MuiDialogContentText-root")
            .forEach(function (note) {
                var text = note.textContent || "";
                if (INTRON.test(text) && text.length < 400) {
                    hide(note);
                }
            });
    }

    var pending = null;

    function schedule() {
        if (pending) {
            return;
        }
        pending = window.requestAnimationFrame(function () {
            pending = null;
            scrub(document.body);
        });
    }

    function start() {
        scrub(document.body);
        new MutationObserver(schedule).observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
