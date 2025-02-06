import type JQueryStatic from 'jquery';

declare global {
  interface Window {
    $: JQueryStatic;
  }
}