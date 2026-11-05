# Dashboard UI audit — 5 November 2026

## Corrected causes

- Overview extended `admin/base.html` and missed the font/styles injected only
  through `admin/base_site.html`. Theme assets now load once through the shared
  base used by Overview, model lists, forms and reports.
- Broad descendant font rules broke Material Symbols, including the nested
  theme label. Normal text now inherits locally served Tajawal. Header account
  and theme controls use SVG, and remaining Material Symbols retain their font.
- CSS targeted `header` and `aside` elements absent from Unfold's header and
  navigation. Selectors now target the actual header and sidebar components.
- The account menu was right-anchored beside the viewport's left edge. It is
  now anchored toward the content, with viewport limits, keyboard dismissal,
  and a fully visible CSRF-protected logout button.
- Global input padding erased widget-specific room for icons. Unfold's widget
  dimensions are retained; select, date/time, checkbox and editor rules are scoped.
- Overview's separate palette, oversized headings and rounded background were
  replaced with the same neutral panels, font sizes and theme colors as lists.

## Shared styling

- `core/fonts.css`: local Tajawal regular, medium and bold, with OFL license.
- `core/dashboard.css`: shared shell, navigation, menus, forms and Overview.
- `core/reports.css`: report styling scoped to `.dashboard-reports`.
- `website/editor.css`: scoped rich-text editor styling and dark-mode contrast.
- Staff dashboard and login also load the local font stylesheet.
- Search, filters, date/time and upload labels are translated in templates;
  there is no global DOM text-replacement script.
- The Django form renderer uses the project template engine, so widget
  overrides in `templates/unfold/widgets/` are applied to actual form controls.

## Verification

- Django system check and 32 application tests passed.
- Production static collection completed, including hashed CSS/font references.
- An isolated temporary database was used to render 44 registered admin list,
  add and change URLs; all returned HTTP 200 with the shared theme assets.
- Real Chrome checked Overview, departments, users, user creation, page/news
  editors, complaint details and reports, plus the assignment form.
- Desktop (1440 px) and mobile (390 px) checks covered viewport containment,
  sidebar navigation, filtering, theme switching, input spacing and actual logout.
- Browser glyph inspection confirmed that Tajawal was actually rendering text,
  rather than merely being named in a computed font-family fallback list.
- The account menu and logout control were inside the viewport and hit-testable.

The audit did not change complaint state transitions, roles or database schemas.
Deploy with `python manage.py collectstatic --noinput` after pulling the changes.
