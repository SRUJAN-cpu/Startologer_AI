import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FileUploadDialog } from './file-upload-dialog';

describe('FileUploadDialog', () => {
  let component: FileUploadDialog;
  let fixture: ComponentFixture<FileUploadDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FileUploadDialog]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FileUploadDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
