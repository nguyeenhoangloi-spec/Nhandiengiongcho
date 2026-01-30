# 🎨 Dog Breed Recognition - Modern UI Design System

## Design Philosophy

Giao diện hiện đại, sạch sẽ và đồng nhất với focus vào trải nghiệm người dùng.

## Color Palette

### Primary Colors

- **Primary**: `#6366f1` (Indigo)
- **Primary Dark**: `#4f46e5`
- **Primary Light**: `#818cf8`
- **Secondary**: `#8b5cf6` (Purple)
- **Accent**: `#ec4899` (Pink)

### Gradients

```css
--gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--gradient-warm: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
--gradient-cool: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
```

### Semantic Colors

- **Success**: `#10b981` (Green)
- **Warning**: `#f59e0b` (Amber)
- **Error**: `#ef4444` (Red)
- **Info**: `#3b82f6` (Blue)

## Spacing System (8px base)

```css
--space-1: 0.25rem; /* 4px */
--space-2: 0.5rem; /* 8px */
--space-3: 0.75rem; /* 12px */
--space-4: 1rem; /* 16px */
--space-6: 1.5rem; /* 24px */
--space-8: 2rem; /* 32px */
--space-12: 3rem; /* 48px */
```

## Typography

- **Font Family**: System fonts (San Francisco, Segoe UI, Roboto)
- **Base Size**: 16px
- **Line Height**: 1.6
- **Weights**: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)

## Border Radius

- **Small**: `0.25rem` (4px)
- **Medium**: `0.5rem` (8px)
- **Large**: `0.75rem` (12px)
- **XL**: `1rem` (16px)
- **2XL**: `1.5rem` (24px)
- **Full**: `9999px` (Pills/Circles)

## Shadows

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

## Component Classes

### Buttons

- `.btn-primary` - Gradient primary button
- `.btn-outline` - Outline button
- `.btn-large` - Large size
- `.btn-gradient-large` - Large gradient button

### Cards

- `.card` - Basic card container
- `.card-hover` - Card with hover effect
- `.stat-card` - Dashboard stat card
- `.feature-card` - Feature showcase card

### Layout

- `.dashboard-layout` - Main dashboard container
- `.sidebar` - Sidebar navigation
- `.main-content` - Content area
- `.container` - Content wrapper with max-width

### Forms

- `.form-group` - Form field wrapper
- `.form-input` - Text input
- `.select-pro` - Select dropdown
- `.toggle-switch` - Toggle control

## Usage Examples

### Creating a Card

```html
<div class="card card-hover">
  <div class="card-icon">🐕</div>
  <h3>Card Title</h3>
  <p>Card description text</p>
</div>
```

### Using Gradients

```html
<div
  style="background: var(--gradient-primary); color: white; padding: var(--space-8); border-radius: var(--radius-xl);"
>
  <h2>Gradient Background</h2>
</div>
```

### Stat Card

```html
<div class="stat-card stat-card-blue">
  <div class="stat-icon">📊</div>
  <div class="stat-content">
    <div class="stat-number">120+</div>
    <div class="stat-label">Breeds Supported</div>
  </div>
</div>
```

## Responsive Breakpoints

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

## Animation Guidelines

- **Transitions**: `250ms cubic-bezier(0.4, 0, 0.2, 1)`
- **Hover effects**: Subtle transform and shadow changes
- **Page transitions**: Fade in/slide down for modals and alerts

## Accessibility

- Minimum contrast ratio: 4.5:1
- Focus states: Visible outline or ring
- Interactive elements: Min 44x44px touch target
- Semantic HTML: Proper heading hierarchy

## Best Practices

1. Use CSS variables for colors and spacing
2. Maintain consistent spacing with the 8px grid
3. Apply shadows consistently for depth hierarchy
4. Use gradients sparingly for primary CTAs
5. Ensure responsive design for all components
6. Test on multiple devices and browsers

## File Structure

```
static/
├── css/
│   └── style.css          # Main stylesheet
├── images/                # Static images
├── js/                    # JavaScript files
└── uploads/               # User uploads
```

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari 13+, Chrome Android latest

---

**Version**: 2.0
**Last Updated**: January 2026
**Design System**: Modern Gradient UI
