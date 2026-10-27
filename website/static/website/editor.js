(function () {
  function initEditors() {
    if (!window.Quill) return;
    const Size = Quill.import('attributors/style/size');
    Size.whitelist = ['14px', '16px', '18px', '24px', '32px', '40px'];
    Quill.register(Size, true);
    const Align = Quill.import('attributors/class/align');
    Align.whitelist = ['left', 'right', 'center', 'justify'];
    Quill.register(Align, true);
    document.querySelectorAll('.council-editor:not(.editor-ready)').forEach(function (wrapper) {
      const textarea = wrapper.querySelector('textarea');
      const feedback = wrapper.querySelector('.editor-feedback');
      const fileInput = wrapper.querySelector('.editor-image-file');
      const form = wrapper.closest('form');
      const editor = new Quill(wrapper.querySelector('.editor-surface'), {
        theme: 'snow',
        placeholder: 'اكتب محتوى الصفحة هنا…',
        formats: ['header', 'size', 'bold', 'italic', 'underline', 'list', 'align', 'direction', 'link', 'image'],
        modules: {toolbar: wrapper.querySelector('.editor-toolbar')}
      });
      editor.root.setAttribute('dir', 'rtl');
      editor.root.setAttribute('aria-label', 'محتوى الصفحة');
      editor.root.setAttribute('role', 'textbox');
      editor.root.setAttribute('aria-multiline', 'true');
      textarea.required = false;
      wrapper.classList.add('editor-ready');
      function sync() {
        textarea.value = editor.getText().trim() || editor.root.querySelector('img') ? editor.getSemanticHTML() : '';
      }
      editor.on('text-change', sync);
      form.addEventListener('submit', function (event) {
        sync();
        if (wrapper.dataset.uploading === 'true') {
          event.preventDefault();
          feedback.textContent = 'انتظر حتى يكتمل رفع الصورة ثم احفظ.';
        } else if (!textarea.value) {
          event.preventDefault();
          feedback.textContent = 'أدخل محتوى الصفحة قبل الحفظ.';
          editor.focus();
        }
      });
      let selection = null;
      editor.getModule('toolbar').addHandler('image', function () {
        selection = editor.getSelection(true);
        fileInput.click();
      });
      fileInput.addEventListener('change', async function () {
        const file = this.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
          feedback.textContent = 'اختر صورة لا يزيد حجمها عن 5 ميغابايت.';
          fileInput.value = '';
          return;
        }
        feedback.textContent = 'جارٍ رفع الصورة…';
        wrapper.dataset.uploading = 'true';
        try {
          const body = new FormData();
          body.append('image', file);
          body.append('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);
          const response = await fetch(wrapper.dataset.uploadUrl, {method: 'POST', body, credentials: 'same-origin'});
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || 'تعذر رفع الصورة.');
          const index = Math.min(selection ? selection.index : editor.getLength() - 1, editor.getLength() - 1);
          editor.insertEmbed(index, 'image', result.url, 'user');
          editor.setSelection(index + 1);
          feedback.textContent = 'تم إدراج الصورة. احفظ الصفحة لتثبيت التغييرات.';
        } catch (error) {
          feedback.textContent = error.message || 'تعذر الاتصال بالخادم. حاول مجدداً.';
        } finally {
          wrapper.dataset.uploading = 'false';
          fileInput.value = '';
        }
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initEditors);
  else initEditors();
})();
